/* 形音义 : service worker.
   Réseau d’abord (4 s au plus), copie locale sinon : l’appli marche hors ligne et prend d’elle-même
   les listes de mots mises à jour dans decks/ dès qu’il y a du réseau. */
const VERSION = "dd02a02900";
const CACHE = "xingyinyi-" + VERSION;
const CORE = ["index.html", "manifest.webmanifest", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png"];
const EXTRA = ["fonts/wenkai.woff2", "fonts/andika-400-ext.woff2", "fonts/andika-400-latin.woff2", "fonts/andika-700-ext.woff2", "fonts/andika-700-latin.woff2", "decks/decks.json", "decks/perso.tsv", "decks/hsk3.tsv", "decks/hsk2.tsv", "decks/hsk1.tsv"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(async cache => {
    await cache.addAll(CORE.map(u => new Request(u, { cache: "reload" })));
    await Promise.all(EXTRA.map(u => cache.add(new Request(u, { cache: "reload" })).catch(() => {})));
  }).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith("xingyinyi-") && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function keyOf(url) {
  const u = new URL(url);
  u.search = ""; u.hash = "";
  if (u.pathname.endsWith("/")) u.pathname += "index.html";
  return u.href;
}
function clean(res) {   // a redirected response cannot answer a page navigation
  return res.redirected ? res.blob().then(b => new Response(b, { status: res.status, statusText: res.statusText, headers: res.headers })) : res;
}

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  const key = keyOf(req.url);
  const network = fetch(req.url, { cache: "no-cache", credentials: "same-origin" });
  // keep a copy of every good answer, even when it arrives after the 4 s fallback
  event.waitUntil(network.then(res => {
    if (!res.ok) return;
    const copy = res.clone();
    return caches.open(CACHE).then(cache => cache.put(key, copy));
  }).catch(() => {}));
  event.respondWith(answer(req, key, network));
});

async function answer(req, key, network) {
  const cached = await caches.open(CACHE).then(cache => cache.match(key));
  const net = network.then(res => (req.mode === "navigate" ? clean(res) : res));
  if (!cached) return net.catch(() => Response.error());
  return new Promise(resolve => {
    const timer = setTimeout(() => resolve(cached), 4000);
    net.then(res => { clearTimeout(timer); resolve(res.ok ? res : cached); },
             () => { clearTimeout(timer); resolve(cached); });
  });
}
