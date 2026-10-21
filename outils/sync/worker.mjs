// 形音义 : serveur de synchronisation (Cloudflare Worker + base D1 liée sous le nom DB).
//
// Un document JSON par code commun, avec un numéro de version. L'appli fusionne elle-même les progressions ; le serveur
// ne fait que garder le document et refuser une écriture faite sur une version dépassée (409), ce qui évite qu'un
// appareil efface ce qu'un autre vient d'envoyer. Le code ne passe jamais en clair : l'appli envoie son empreinte
// SHA-256 (64 caractères hexadécimaux). Une copie du document est gardée au plus une fois par 20 heures, 30 copies au plus.
// Les versions sont des heures en millisecondes (jamais deux fois la même, même si la base est vidée puis recréée). Le nombre
// de codes est limité (MAX_CODES, 5 par défaut, réglable dans les variables du Worker) : l'adresse est publique.
//
//   GET  /sante                       "ok" si la base répond
//   GET  /p/<clé>?have=<v>            {v, data} ({v} seul si l'appareil a déjà la version v ; {v: 0, data: null} si rien)
//   PUT  /p/<clé>   {v, data}         {v: nouvelle version} si le serveur en est toujours à v (0 : premier envoi), sinon
//                                     409 {v, data} ; 403 si le serveur a déjà MAX_CODES codes
//   GET  /p/<clé>/copies              {copies: [{at, v, size}]}, de la plus récente à la plus ancienne
//   GET  /p/<clé>/copies/<at>         {at, v, data}

const MAX = 1000000;                 // taille maximale d'un document (D1 : 2 Mo par ligne ; un dictionnaire entier révisé : 0,6 Mo)
const COPY_EVERY = 20 * 3600e3, COPIES = 30;
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};
const send = (body, status = 200) => new Response(typeof body === "string" ? body : JSON.stringify(body),
  { status, headers: { ...CORS, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" } });

let ready = null;                    // les tables, créées une fois par instance
function tables(db) {
  if (!ready) ready = db.batch([
    db.prepare("CREATE TABLE IF NOT EXISTS docs (k TEXT PRIMARY KEY, v INTEGER NOT NULL, data TEXT NOT NULL, at INTEGER NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS copies (k TEXT NOT NULL, at INTEGER NOT NULL, v INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY (k, at))"),
  ]).catch(e => { ready = null; throw e; });
  return ready;
}
const current = (db, k) => db.prepare("SELECT v, data FROM docs WHERE k = ?").bind(k).first();
const docText = row => `{"v":${row.v},"data":${row.data}}`;

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    if (!env.DB) return send({ error: "base D1 non liée (variable DB)" }, 500);
    const url = new URL(req.url), path = url.pathname.replace(/\/+$/, "");
    try {
      await tables(env.DB);
      if (path === "/sante" && req.method === "GET") return send('"ok"');
      const m = /^\/p\/([0-9a-f]{64})(\/copies(?:\/(\d{1,16}))?)?$/.exec(path);
      if (!m) return send({ error: "adresse inconnue" }, 404);
      const k = m[1];

      if (m[2]) {                    // the daily copies
        if (req.method !== "GET") return send({ error: "méthode refusée" }, 405);
        if (m[3]) {
          const row = await env.DB.prepare("SELECT at, v, data FROM copies WHERE k = ? AND at = ?").bind(k, +m[3]).first();
          return row ? send(`{"at":${row.at},"v":${row.v},"data":${row.data}}`) : send({ error: "copie introuvable" }, 404);
        }
        const { results } = await env.DB.prepare("SELECT at, v, length(data) AS size FROM copies WHERE k = ? ORDER BY at DESC").bind(k).all();
        return send({ copies: results || [] });
      }

      if (req.method === "GET") {
        const row = await current(env.DB, k);
        if (!row) return send({ v: 0, data: null });
        if (url.searchParams.get("have") === String(row.v)) return send({ v: row.v });
        return send(docText(row));
      }

      if (req.method === "PUT") {
        if (+(req.headers.get("Content-Length") || 0) > 2 * MAX) return send({ error: "document trop gros" }, 413);
        const text = await req.text();
        if (text.length > 2 * MAX) return send({ error: "document trop gros" }, 413);
        let body;
        try { body = JSON.parse(text); } catch (e) { return send({ error: "JSON illisible" }, 400); }
        if (!body || !Number.isInteger(body.v) || body.v < 0 || !body.data || typeof body.data !== "object" || Array.isArray(body.data))
          return send({ error: "il faut {v, data}" }, 400);
        const data = JSON.stringify(body.data), now = Date.now(), v = Math.max(body.v + 1, now);
        if (data.length > MAX) return send({ error: "document trop gros" }, 413);
        let res;
        if (body.v === 0) {
          res = await env.DB.prepare("INSERT INTO docs (k, v, data, at) SELECT ?, ?, ?, ? WHERE (SELECT count(*) FROM docs) < ? ON CONFLICT (k) DO NOTHING")
            .bind(k, v, data, now, +env.MAX_CODES || 5).run();
        } else {
          // the version about to be replaced is kept as a copy if the last copy is older than COPY_EVERY
          const out = await env.DB.batch([
            env.DB.prepare("INSERT OR IGNORE INTO copies (k, at, v, data) SELECT k, ?, v, data FROM docs WHERE k = ? AND v = ? " +
              "AND NOT EXISTS (SELECT 1 FROM copies WHERE k = ? AND at > ?)").bind(now, k, body.v, k, now - COPY_EVERY),
            env.DB.prepare("UPDATE docs SET v = ?, data = ?, at = ? WHERE k = ? AND v = ?").bind(v, data, now, k, body.v),
            env.DB.prepare("DELETE FROM copies WHERE k = ? AND at NOT IN (SELECT at FROM copies WHERE k = ? ORDER BY at DESC LIMIT ?)").bind(k, k, COPIES),
          ]);
          res = out[1];
        }
        if (res && res.meta && res.meta.changes === 1) return send({ v });
        const row = await current(env.DB, k);       // someone wrote in between: here is what the server has now
        if (!row && body.v === 0) return send({ error: "serveur complet : il a déjà tous les codes qu’il accepte (MAX_CODES)" }, 403);
        return send(row ? docText(row) : { v: 0, data: null }, 409);
      }
      return send({ error: "méthode refusée" }, 405);
    } catch (e) {
      if (/no such table/i.test(String(e && e.message))) ready = null;   // the base was emptied: the tables again next time
      return send({ error: "erreur du serveur : " + (e && e.message || e) }, 500);
    }
  },
};
