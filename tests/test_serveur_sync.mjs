// 形音义 : tests du serveur de synchronisation (outils/sync/worker.mjs), sans réseau : node tests/test_serveur_sync.mjs
import { DatabaseSync } from "node:sqlite";
import worker from "../outils/sync/worker.mjs";

const sql = new DatabaseSync(":memory:");
function statement(text, params = []) {
  return {
    bind: (...p) => statement(text, p),
    first: async () => sql.prepare(text).get(...params) ?? null,
    all: async () => ({ results: sql.prepare(text).all(...params) }),
    run: async () => ({ meta: { changes: Number(sql.prepare(text).run(...params).changes) } }),
    _now: () => (/^\s*select/i.test(text) ? { results: sql.prepare(text).all(...params), meta: {} } : { meta: { changes: Number(sql.prepare(text).run(...params).changes) } }),
  };
}
const DB = {
  prepare: t => statement(t),
  batch: async list => { sql.exec("BEGIN"); try { const o = list.map(s => s._now()); sql.exec("COMMIT"); return o; } catch (e) { sql.exec("ROLLBACK"); throw e; } },
};

let fails = 0, oks = 0;
function check(cond, label, detail) {
  if (cond) { oks++; console.log("  ok   " + label); }
  else { fails++; console.log("  ÉCHEC " + label + (detail === undefined ? "" : " : " + JSON.stringify(detail))); }
}
let clock = Date.parse("2026-10-21T08:00:00Z");
Date.now = () => clock;
let env = { DB };
async function call(method, path, body) {
  const res = await worker.fetch(new Request("https://sync.test" + path, { method, headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body) }), env);
  const text = await res.text();
  let json = null; try { json = JSON.parse(text); } catch (e) {}
  return { status: res.status, json, cors: res.headers.get("Access-Control-Allow-Origin") };
}
const K = "a".repeat(64), K2 = "b".repeat(64);

check((await call("GET", "/sante")).json === "ok", "health: the base answers");
check((await worker.fetch(new Request("https://sync.test/sante"), {})).status === 500, "no D1 binding: a clear error");
const pre = await worker.fetch(new Request("https://sync.test/p/" + K, { method: "OPTIONS" }), env);
check(pre.status === 204 && pre.headers.get("Access-Control-Allow-Methods").includes("PUT"), "CORS preflight");
check((await call("GET", "/p/court")).status === 404, "a key that is not a SHA-256: refused");

let r = await call("GET", "/p/" + K);
check(r.status === 200 && r.json.v === 0 && r.json.data === null && r.cors === "*", "nothing yet: v 0, no data", r);
r = await call("PUT", "/p/" + K, { v: 0, data: { cards: { a: { b: 1 } } } });
const v1 = r.json && r.json.v;
check(r.status === 200 && v1 === clock, "first write: its version is the hour (ms)", r);
r = await call("PUT", "/p/" + K, { v: 0, data: { cards: { x: {} } } });
check(r.status === 409 && r.json.v === v1 && r.json.data.cards.a.b === 1, "a second « first write »: refused, with what the server has", r);
r = await call("GET", "/p/" + K);
check(r.json.v === v1 && r.json.data.cards.a.b === 1, "read back", r);
r = await call("GET", `/p/${K}?have=${v1}`);
check(r.json.v === v1 && !("data" in r.json), "already up to date: the version only", r);

r = await call("PUT", "/p/" + K, { v: v1, data: { cards: { a: { b: 2 } } } });
const v2 = r.json && r.json.v;
check(r.status === 200 && v2 === v1 + 1, "write on the right version, in the same millisecond: v + 1", r);
r = await call("PUT", "/p/" + K, { v: v1, data: { cards: { a: { b: 9 } } } });
check(r.status === 409 && r.json.v === v2 && r.json.data.cards.a.b === 2, "write on an old version: 409 and the current document", r);
check((await call("GET", "/p/" + K2)).json.v === 0, "another code: another document");

let c = await call("GET", `/p/${K}/copies`);
check(c.json.copies.length === 1 && c.json.copies[0].v === v1, "the version replaced is kept as a copy", c.json);
clock += 3600e3;
r = await call("PUT", "/p/" + K, { v: v2, data: { cards: { a: { b: 3 } } } });
let v = r.json.v;
check(v === clock, "later: the version is the hour again", r.json);
c = await call("GET", `/p/${K}/copies`);
check(c.json.copies.length === 1, "no second copy within 20 hours", c.json);
for (let i = 0; i < 35; i++) { clock += 21 * 3600e3; v = (await call("PUT", "/p/" + K, { v, data: { cards: { a: { b: 4 + i } } } })).json.v; }
c = await call("GET", `/p/${K}/copies`);
check(c.json.copies.length === 30 && c.json.copies[0].at > c.json.copies[29].at, "one copy a day, 30 at most, the newest first", c.json.copies.length);
const one = await call("GET", `/p/${K}/copies/${c.json.copies[0].at}`);
check(one.json.v === c.json.copies[0].v && one.json.data.cards.a.b === 37, "a copy, read back: the version before the last", one.json);
check((await call("GET", `/p/${K}/copies/12345`)).status === 404, "a copy that is not there: 404");

check((await call("PUT", "/p/" + K, "pas du json")).status === 400, "bad JSON: 400");
check((await call("PUT", "/p/" + K, { v: -1, data: {} })).status === 400, "bad version: 400");
check((await call("PUT", "/p/" + K, { v: 1, data: [1] })).status === 400, "data must be an object: 400");
check((await call("PUT", "/p/" + K, { v, data: { big: "x".repeat(1000001) } })).status === 413, "too big: 413");
check((await call("DELETE", "/p/" + K)).status === 405, "other methods: 405");

// the base emptied (a new D1, a mistake): the versions never come back, so no device takes an old one for the current
const old = v;
sql.exec("DELETE FROM docs");
clock += 1000;
r = await call("PUT", "/p/" + K, { v: old, data: { cards: {} } });
check(r.status === 409 && r.json.v === 0, "the server lost the document: an old version is refused (nothing there)", r.json);
r = await call("PUT", "/p/" + K, { v: 0, data: { cards: { z: { b: 1 } } } });
check(r.status === 200 && r.json.v > old, "written again: a version above every one of before", [r.json.v, old]);

// the address is public: a limited number of codes
env = { DB, MAX_CODES: "2" };
check((await call("PUT", "/p/" + K2, { v: 0, data: { cards: {} } })).status === 200, "a second code");
r = await call("PUT", "/p/" + "c".repeat(64), { v: 0, data: { cards: {} } });
check(r.status === 403 && /complet/.test(r.json.error), "a third code with MAX_CODES = 2: 403, server full", r.json);
r = await call("PUT", "/p/" + K2, { v: 0, data: { cards: {} } });
check(r.status === 409, "a code already there still gets its 409 when full", r.status);

console.log(`\n${oks} ok, échecs : ${fails || "aucun"}`);
process.exit(fails ? 1 : 0);
