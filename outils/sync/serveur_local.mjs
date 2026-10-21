// 形音义 : le serveur de synchronisation (worker.mjs) sur cet ordinateur, pour les tests et pour essayer sans Cloudflare.
// La base D1 est imitée par node:sqlite (Node 22.13 ou plus).
//
//   node outils/sync/serveur_local.mjs [--port 8787] [--base fichier.sqlite]     (sans --base : en mémoire)
//
// L'adresse à donner à l'appli est alors http://localhost:8787.

import http from "node:http";
import { DatabaseSync } from "node:sqlite";
import worker from "./worker.mjs";

const arg = (name, dflt) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : dflt; };
const port = +arg("--port", 8787), file = arg("--base", ":memory:");
const sql = new DatabaseSync(file);

// the part of the D1 API the worker uses
function statement(text, params = []) {
  return {
    bind: (...p) => statement(text, p),
    first: async () => sql.prepare(text).get(...params) ?? null,
    all: async () => ({ results: sql.prepare(text).all(...params), success: true }),
    run: async () => { const r = sql.prepare(text).run(...params); return { success: true, meta: { changes: Number(r.changes) } }; },
    _now: () => { const st = sql.prepare(text); return /^\s*select/i.test(text) ? { results: st.all(...params), meta: {} } : { meta: { changes: Number(st.run(...params).changes) } }; },
  };
}
const DB = {
  prepare: text => statement(text),
  batch: async list => {                   // D1 runs a batch as one transaction
    sql.exec("BEGIN");
    try { const out = list.map(s => s._now()); sql.exec("COMMIT"); return out; }
    catch (e) { sql.exec("ROLLBACK"); throw e; }
  },
};

http.createServer(async (req, res) => {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const body = chunks.length ? Buffer.concat(chunks) : undefined;
  const request = new Request(`http://localhost:${port}${req.url}`, {
    method: req.method, headers: req.headers, body: ["GET", "HEAD", "OPTIONS"].includes(req.method) ? undefined : body });
  const out = await worker.fetch(request, { DB });
  res.writeHead(out.status, Object.fromEntries(out.headers));
  res.end(Buffer.from(await out.arrayBuffer()));
}).listen(port, "127.0.0.1", () => console.log(`serveur de synchronisation : http://localhost:${port} (base ${file})`));
