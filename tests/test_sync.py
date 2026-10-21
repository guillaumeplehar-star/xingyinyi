# -*- coding: utf-8 -*-
"""Progression partagée entre deux appareils (un téléphone A et un ordinateur B) par le serveur de synchronisation
(outils/sync/worker.mjs, lancé sur cet ordinateur par outils/sync/serveur_local.mjs, base SQLite en mémoire).

Créer un code, le rejoindre (seules ses lettres et chiffres comptent), un mot changé d'un seul côté (ce côté, même plus
bas), un mot changé des deux côtés (le plus avancé, révisions additionnées), historique additionné, mots et listes du
téléphone, suppressions, réglages (la voix reste à chaque appareil), listes plus anciennes sur un appareil, réponse du
serveur perdue (rien compté deux fois), deux fenêtres sur l'ordinateur, mot du téléphone passé dans decks/ sur un appareil
et révisé sur l'autre, arrêt pendant un échange, test complet en cours, ordre de « Ajoutés ici », hors ligne,
synchronisation au démarrage et à la mise en arrière-plan, version plus récente refusée, copies du serveur, arrêt, code
tapé que personne n'utilise, bouton Installer.
Lancer depuis la racine du dépôt :  py tests\\test_sync.py      (demande Node 22.13 ou plus)
"""
import hashlib
import json
import os
import re
import socket
import subprocess
import time
import unicodedata
import urllib.request

from playwright.sync_api import sync_playwright

from commun import REPO, check, serve, fresh_copy, wait_ready, answer, shot, finish, nb


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_server():
    port = free_port()
    proc = subprocess.Popen(["node", os.path.join(REPO, "outils", "sync", "serveur_local.mjs"), "--port", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = "http://127.0.0.1:%d" % port
    for _ in range(100):
        try:
            if json.loads(urllib.request.urlopen(url + "/sante", timeout=1).read()) == "ok":
                return proc, url
        except Exception:
            time.sleep(0.1)
    raise SystemExit("le serveur de synchronisation ne démarre pas (Node 22.13 ou plus ?)")


def key_of(code):
    """As the app: only the letters and digits of the code count (codeKey)."""
    k = "".join(c for c in unicodedata.normalize("NFKD", code) if not unicodedata.combining(c)).lower()
    return hashlib.sha256(("xingyinyi:" + re.sub(r"[^a-z0-9]", "", k)).encode("utf-8")).hexdigest()


def server_doc(url, code):
    return json.loads(urllib.request.urlopen("%s/p/%s" % (url, key_of(code))).read())


def server_put(url, code, v, data):
    req = urllib.request.Request("%s/p/%s" % (url, key_of(code)), method="PUT", data=json.dumps({"v": v, "data": data}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {"status": e.code, **json.loads(e.read())}


def device(browser, errors, name, size, mobile, scheme="light"):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=2 if mobile else 1,
                              is_mobile=mobile, has_touch=mobile, color_scheme=scheme, locale="fr-FR")
    return ctx, watch(ctx.new_page(), errors, name)


def watch(page, errors, name):
    def on_console(m):
        # the server's 409 (a write on an old version, merged again) and the offline step are expected
        if m.type in ("error", "warning") and not re.search(r"409|Conflict|ERR_INTERNET_DISCONNECTED|Failed to fetch|net::", m.text):
            errors.append("%s %s: %s" % (name, m.type, m.text))
    page.on("console", on_console)
    page.on("pageerror", lambda e: errors.append("%s pageerror: %s" % (name, e)))
    return page


SYNC = """async () => { for (let i = 0; i < 200 && syncBusy; i++) await new Promise(r => setTimeout(r, 50)); return await syncNow(true); }"""
FREEZE = "() => { if (!window.__ss) window.__ss = syncSoon; syncSoon = () => {}; clearTimeout(syncTimer); syncTimer = 0; }"   # no sync of its own
THAW = "() => { if (window.__ss) syncSoon = window.__ss; }"
CARDS = "(ids) => Object.fromEntries(ids.map(id => [id, state.cards[id] ? { ...state.cards[id] } : null]))"
GRADE = "([id, ok]) => { applyGrade(id, ok); save(); rebuildDeck(); }"
FRESH = "(n) => lineOf(dayNum()).filter(id => inPass(id) && !id.startsWith('perso:')).slice(0, n)"   # words seen nowhere yet
LOG = "() => { const d = state.log[dayNum()] || {}; return { n: d.n || 0, r: d.r || 0, p: d.p || 0 }; }"


def main():
    errors = []
    srv, SURL = start_server()
    site_b = fresh_copy("site-sync-b")
    site_a = fresh_copy("site-sync-a")
    with open(os.path.join(site_a, "decks", "perso.tsv"), "a", encoding="utf-8") as fh:
        fh.write("测试\tcèshì\ttester ; essai\n")      # a word only device A's lists have (newer lists)
    for site in (site_a, site_b):                       # the copies talk to the local server, not to Cloudflare
        page = os.path.join(site, "index.html")
        with open(page, encoding="utf-8") as fh:
            html = fh.read()
        html, n = re.subn(r'const SYNC_URL = "[^"]*";', 'const SYNC_URL = "%s/";' % SURL, html)
        assert n == 1, "SYNC_URL introuvable dans index.html"
        with open(page, "w", encoding="utf-8", newline="") as fh:
            fh.write(html)
    httpd_b, url_b = serve(site_b)
    httpd_a, url_a = serve(site_a)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # B, the computer, opens first: its lists are older than A's
            ctx_b, B = device(browser, errors, "B", (1280, 800), False)
            B.goto(url_b)
            wait_ready(B)
            B.wait_for_timeout(50)
            ctx_a, A = device(browser, errors, "A", (390, 844), True)
            A.goto(url_a)
            wait_ready(A)
            for P in (A, B):
                P.evaluate(FREEZE)

            # ------------------------------------------------------------ A creates a code
            print("== créer un code (A)")
            a3 = [answer(A, 1), answer(A, 1), answer(A, 0)]
            A.evaluate("() => { state.settings.evalSize = 35; state.settings.rate = 0.6; state.settings.autoAudio = false; save(); }")
            A.click(".tab[data-view='settings']")
            A.click("[data-sync='new']")
            code = A.input_value("#sync-code")
            check(re.fullmatch(r"([a-z]+-){4}\d{2}", code) is not None, "Créer un code: four pinyin syllables and a number", code)
            check(not A.is_hidden("#sync-hint") and "Utiliser ce code" in nb(A.text_content("#sync-hint")), "a hint to note the code", A.text_content("#sync-hint"))
            A.click("[data-sync='join']")
            A.wait_for_function("() => { const c = syncCfg(); return c && c.at > 0; }")
            A.wait_for_function("() => document.querySelector('#toast').textContent.includes('Code créé')")
            A.evaluate(FREEZE)
            doc = server_doc(SURL, code)
            cards_a = A.evaluate(CARDS, a3)
            check(doc["v"] > 0 and all(doc["data"]["cards"].get(i) == cards_a[i] for i in a3),
                  "the server has A's progress", (doc["v"], list(doc["data"]["cards"])[:5]))
            check(doc["data"]["settings"].get("evalSize") == 35 and "rate" not in doc["data"]["settings"] and "autoAudio" not in doc["data"]["settings"],
                  "settings shared, the voice left out", doc["data"]["settings"])
            check(A.is_hidden("#sync-url") and A.evaluate("() => syncCfg().url") == SURL,
                  "the server's address is in the app (no field), kept without its final /", A.evaluate("() => syncCfg().url"))
            st = nb(A.text_content("#sync-status"))
            check(st.startswith("Synchronisé à l’instant") and code in nb(A.text_content("#sync-box")), "settings: the code and « Synchronisé à l’instant »", st)
            check("serveur de synchronisation" in nb(A.text_content("#storage-note")), "the backup note tells about the server", A.text_content("#storage-note"))
            shot(A, "sync-01-code")

            # ------------------------------------------------------------ B joins
            print("== rejoindre (B)")
            A.evaluate("() => { state.lists.push({ id: 'p-avant', nom: 'Avant', ids: ['perso:测试'] }); save(); rebuildDeck(); }")
            A.evaluate(SYNC)                               # a list with a word B's older lists do not have, before B joins
            B.evaluate("() => { state.settings.rate = 1.0; save(); }")
            B.click(".tab[data-view='settings']")
            B.fill("#sync-code", "  " + code.upper().replace("-", "") + " ")      # typed without its dashes, in capitals: same code
            B.click("[data-sync='join']")
            B.wait_for_function("() => { const c = syncCfg(); return c && c.at > 0; }")
            B.wait_for_function("() => document.querySelector('#toast').textContent.includes('Code enregistré')")
            B.evaluate(FREEZE)
            check(B.evaluate("() => syncCfg().key") == key_of(code), "B: the same code, typed in capitals without dashes", B.evaluate("() => syncCfg().code"))
            check(B.evaluate(CARDS, a3) == cards_a, "B has A's progress, word by word", B.evaluate(CARDS, a3))
            sb = B.evaluate("() => state.settings")
            check(sb["evalSize"] == 35 and sb["rate"] == 1.0 and sb["autoAudio"] is True, "B: A's settings, its own voice", sb)
            check(B.evaluate(LOG) == A.evaluate(LOG), "B: A's history (Progrès)", (B.evaluate(LOG), A.evaluate(LOG)))
            pre = B.evaluate("() => ({ ids: (state.lists.find(x => x.id === 'p-avant') || {}).ids, behind: listsBehind() })")
            check(pre["behind"] and pre["ids"] == ["perso:测试"], "joining with older lists: a word B does not know stays in A's list", pre)
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            check(A.evaluate("() => state.lists.find(x => x.id === 'p-avant').ids") == ["perso:测试"], "and stays on A")
            shot(B, "sync-02-ordinateur")

            # ------------------------------------------------------------ a word changed on one side only
            print("== changé d'un seul côté")
            w = a3[0]                                      # √ on A: bucket 1
            B.evaluate(GRADE, [w, False])
            B.evaluate(SYNC)
            r = A.evaluate(SYNC)
            cw = A.evaluate(CARDS, [w])[w]
            check(r["ok"] and cw["b"] == 0 and cw.get("k") and cw["l"] == 1 and cw["r"] == 2,
                  "missed on B only: A takes it, even lower (not a conflict)", cw)

            # ------------------------------------------------------------ the same word on both sides
            print("== changé des deux côtés")
            x = a3[1]                                      # bucket 1 on both
            rx = A.evaluate(CARDS, [x])[x]["r"]
            A.evaluate(GRADE, [x, True])                   # bucket 2 on A
            B.evaluate(GRADE, [x, False])                  # bucket 0 on B
            y, z = A.evaluate(FRESH, 2)
            A.evaluate(GRADE, [y, True])                   # two other words, one on each side
            B.evaluate(GRADE, [z, False])
            A.evaluate("() => { state.settings.learnSize = 30; save(); }")
            B.evaluate("() => { state.settings.learnSize = 40; save(); }")
            puts_b = []
            B.on("response", lambda res: puts_b.append(res.status) if res.request.method == "PUT" and res.url.startswith(SURL) else None)
            A.evaluate(SYNC)
            rb = B.evaluate(SYNC)                          # B writes on an old version: 409, merge, write again
            A.evaluate(SYNC)
            ca, cb = A.evaluate(CARDS, [x, y, z]), B.evaluate(CARDS, [x, y, z])
            check(rb["ok"] and ca == cb, "after the merge both devices agree", (ca, cb))
            check(ca[x]["b"] == 2 and ca[x]["r"] == rx + 2, "the word changed on both: the more advanced progress (bucket 2), reviews added", ca[x])
            check(ca[y] and ca[y]["b"] == 1 and ca[z] and ca[z]["b"] == 0 and ca[z].get("k"), "the other words: each side's", ca)
            check(puts_b == [409, 200], "B's write on an old version: refused, merged, written again", puts_b)
            la, lb = A.evaluate(LOG), B.evaluate(LOG)
            check(la == lb and la["n"] + la["r"] == 3 + 2 + 3, "history: the reviews of both devices add up", (la, lb))
            check(A.evaluate("() => state.settings.learnSize") == B.evaluate("() => state.settings.learnSize") == 40,
                  "a setting changed on both: the device that merged keeps its own, then both have it", A.evaluate("() => state.settings.learnSize"))
            check(A.evaluate("() => state.settings.rate") == 0.6 and B.evaluate("() => state.settings.rate") == 1.0, "each device keeps its voice speed")

            # ------------------------------------------------------------ words and lists of a device
            print("== mots et listes")
            A.evaluate("""() => { state.custom.push({ id: 'u-voy1', h: '登机牌', p: 'dēngjīpái', f: 'carte d’embarquement' });
                state.lists.push({ id: 'p-voyage', nom: 'Voyage', ids: ['u-voy1', 'perso:测试'] }); save(); rebuildDeck(); }""")
            A.evaluate(SYNC)
            B.evaluate(SYNC)
            got = B.evaluate("""() => { const L = LISTBYID.get('p-voyage'); return { list: L && L.nom, words: L ? L.words.map(w => w.h) : [],
                ids: (state.lists.find(x => x.id === 'p-voyage') || {}).ids, word: (BYID.get('u-voy1') || {}).f, behind: listsBehind() }; }""")
            check(got["list"] == "Voyage" and got["word"] == "carte d’embarquement" and "登机牌" in got["words"], "B: the list and the word made on A", got)
            check(got["behind"] and "perso:测试" in got["ids"], "B's lists are older: the word it does not know stays in the list", got)
            B.evaluate(GRADE, [y, True])
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            ids_a = A.evaluate("() => state.lists.find(x => x.id === 'p-voyage').ids")
            check("perso:测试" in ids_a and A.evaluate("() => LISTBYID.get('p-voyage').words.length") == 2, "back on A, the list still has it", ids_a)
            B.evaluate("() => { state.lists = state.lists.filter(x => x.id !== 'p-voyage'); save(); rebuildDeck(); }")
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            check(not A.evaluate("() => state.lists.some(x => x.id === 'p-voyage')"), "a list deleted on B goes on A too")

            # ------------------------------------------------------------ put back to zero
            print("== remise à zéro")
            A.evaluate("(id) => { delete state.cards[id]; save(); }", y)       # A: y back to zero; B reviews it meanwhile
            B.evaluate(GRADE, [y, True])
            A.evaluate("(id) => { delete state.cards[id]; save(); }", z)       # z: back to zero on A only
            A.evaluate(SYNC)
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            cy, cz = A.evaluate(CARDS, [y, z]), B.evaluate(CARDS, [y, z])
            check(cy[y] and cy[y]["b"] >= 2 and cz[y] == cy[y], "put back to zero on A, reviewed on B: the progress stays", (cy, cz))
            check(cy[z] is None and cz[z] is None, "put back to zero on A only: gone on B too", (cy[z], cz[z]))

            # ------------------------------------------------------------ a write the server got, its answer lost
            print("== réponse perdue")
            B.evaluate(SYNC)
            q, q2 = A.evaluate(FRESH, 2)
            log0 = B.evaluate(LOG)
            B.evaluate(GRADE, [q, True])

            def lose(route):
                if route.request.method == "PUT":
                    route.fetch()                          # the server gets it…
                    route.abort()                          # …and the answer never comes back (the app went to sleep)
                else:
                    route.continue_()
            B.route(SURL + "/p/**", lose)
            r = B.evaluate(SYNC)
            B.unroute(SURL + "/p/**")
            check(not r["ok"] and server_doc(SURL, code)["data"]["cards"].get(q, {}).get("r") == 1, "the server got the write, B did not hear back", r)
            B.evaluate(GRADE, [q2, True])
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            cq, log1 = A.evaluate(CARDS, [q, q2]), B.evaluate(LOG)
            check(cq[q]["r"] == 1 and cq[q2]["r"] == 1 and log1["n"] == log0["n"] + 2 and A.evaluate(LOG) == log1,
                  "next sync: the lost write is B's own, nothing counted twice", (cq, log0, log1))

            # ------------------------------------------------------------ two windows of the app on the computer
            print("== deux fenêtres")
            A2 = watch(ctx_a.new_page(), errors, "A2")
            A2.goto(url_a)
            wait_ready(A2)
            A2.evaluate(FREEZE)
            w2 = A2.evaluate(FRESH, 1)[0]
            A2.evaluate(GRADE, [w2, True])
            A.wait_for_function("(id) => !!state.cards[id]", arg=w2, timeout=5000)
            check(True, "another window saves: this one goes on from there")
            A2.evaluate(SYNC)
            A.evaluate(SYNC)
            check((server_doc(SURL, code)["data"]["cards"].get(w2) or {}).get("b") == 1, "the first window's sync keeps what the second did")
            A2.close()

            # ------------------------------------------------------------ a word of the phone moved to decks/ on one side
            print("== mot passé dans decks/")
            B.evaluate("""() => { state.custom.push({ id: 'u-zxg', h: '照相馆', p: 'zhàoxiàngguǎn', f: 'studio de photo' });
                state.tel.push('u-zxg'); applyGrade('u-zxg', true, null, 0); save(); rebuildDeck(); }""")
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            with open(os.path.join(site_a, "decks", "perso.tsv"), "a", encoding="utf-8") as fh:
                fh.write("照相馆\tzhàoxiàngguǎn\tstudio de photo\n")      # copied for the computer, published
            A.evaluate("async () => { await refreshLists(false, true); }")
            mv = A.evaluate("() => ({ moved: state.moved['u-zxg'], card: state.cards['perso:照相馆'], old: !!state.cards['u-zxg'] })")
            check(mv["moved"] == "perso:照相馆" and mv["card"] and not mv["old"], "A: the word moves to its line in perso.tsv", mv)
            B.evaluate("() => { applyGrade('u-zxg', true, null, 0); save(); }")      # B reviews it meanwhile, under its old id
            A.evaluate(SYNC)
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            got = [P.evaluate("() => [state.cards['u-zxg'] || null, state.cards['perso:照相馆'], state.custom.some(w => w.id === 'u-zxg')]") for P in (A, B)]
            check(got[0] == got[1] and got[0][0] is None and got[0][1]["b"] == 2 and got[0][1]["r"] == 2 and not got[0][2],
                  "B's review follows the word to its new id: bucket 2, two reviews, no card left behind", got)

            # ------------------------------------------------------------ « Arrêter » while the server answers
            print("== arrêt pendant un échange")
            B.evaluate(GRADE, [q, False])
            res = B.evaluate("""async () => { const c = localStorage.getItem('xingyinyi.sync'), b = localStorage.getItem('xingyinyi.sync-base');
                const p = syncNow(true); writeSyncCfg(null); writeBase(0, null);
                const r = await p, out = { r, cfg: syncCfg(), base: localStorage.getItem('xingyinyi.sync-base') };
                localStorage.setItem('xingyinyi.sync', c); localStorage.setItem('xingyinyi.sync-base', b); return out; }""")
            check(res["r"] is None and res["cfg"] is None and res["base"] is None, "stopped during an exchange: nothing written back", res)
            B.evaluate(SYNC)
            A.evaluate(SYNC)

            # ------------------------------------------------------------ a full test in progress
            print("== test complet en cours")
            A.evaluate("() => { showView('study'); study.startTest(['hsk1']); }")
            t1 = answer(A, 1)
            B.evaluate(GRADE, [B.evaluate(FRESH, 1)[0], True])
            B.evaluate(SYNC)
            got = A.evaluate(SYNC)
            t2 = answer(A, 0)
            t = A.evaluate("() => ({ ok: state.test.ok.map(p => p[0]), ko: state.test.ko.map(p => p[0]), same: study.res === state.test })")
            check(got["n"] >= 1 and t1 in t["ok"] and t2 in t["ko"] and t["same"], "progress arrives during a test: the test keeps every answer", (got, t))
            A.evaluate("() => { state.test = null; save(); study.build(); }")

            # ------------------------------------------------------------ « Ajoutés ici » on both sides
            print("== ordre de « Ajoutés ici »")
            A.evaluate("() => { state.custom.push({ id: 'u-ta', h: '火车票', p: 'huǒchēpiào', f: 'billet de train' }); state.tel.push('u-ta'); save(); rebuildDeck(); }")
            B.evaluate("() => { state.custom.push({ id: 'u-tb', h: '飞机票', p: 'fēijīpiào', f: 'billet d’avion' }); state.tel.push('u-tb'); save(); rebuildDeck(); }")
            for P in (A, B, A, B):
                P.evaluate(SYNC)
            va = server_doc(SURL, code)["v"]
            for P in (A, B, A):
                P.evaluate(SYNC)
            tels = [P.evaluate("() => state.tel") for P in (A, B)]
            check(server_doc(SURL, code)["v"] == va and tels[0] == tels[1] and "u-ta" in tels[0] and "u-tb" in tels[0],
                  "a word added on each side: the same order everywhere, then no more writes", tels)

            # ------------------------------------------------------------ offline
            print("== hors ligne")
            ctx_b.set_offline(True)
            u = A.evaluate(FRESH, 3)[2]
            B.evaluate(GRADE, [u, True])
            r = B.evaluate(SYNC)
            check(not r["ok"] and "connexion" in r["err"], "offline: the sync waits", r)
            B.evaluate("() => renderSettings()")
            check("Dernier essai" in nb(B.text_content("#sync-status")) and B.evaluate("() => $('#sync-status').classList.contains('err')"),
                  "settings tell the last attempt failed", B.text_content("#sync-status"))
            shot(B, "sync-03-hors-ligne")
            ctx_b.set_offline(False)
            B.evaluate(SYNC)
            A.evaluate(SYNC)
            check((A.evaluate(CARDS, [u])[u] or {}).get("b") == 1, "back online: what was done offline arrives", A.evaluate(CARDS, [u]))

            # ------------------------------------------------------------ automatic syncs
            print("== synchronisations automatiques")
            v1 = server_doc(SURL, code)["v"]
            A.evaluate(THAW)
            u2 = A.evaluate(FRESH, 4)[3]
            A.evaluate(GRADE, [u2, True])
            check(A.evaluate("() => !!syncTimer && syncDirtyAt > 0"), "a change: a sync is planned", A.evaluate("() => [syncTimer, syncDirtyAt]"))
            A.evaluate("""() => { Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' });
                document.dispatchEvent(new Event('visibilitychange')); delete document.visibilityState; }""")
            A.wait_for_function("() => !syncBusy && syncDirtyAt === 0")
            d = server_doc(SURL, code)
            check(d["v"] > v1 and d["data"]["cards"].get(u2, {}).get("b") == 1, "the app goes to the background: sent at once", d["v"])
            A.evaluate(FREEZE)
            B.evaluate(SYNC)                               # B has A's √ first: its × is then a change of its own
            B.evaluate(GRADE, [u2, False])
            B.evaluate(SYNC)
            A.reload()
            wait_ready(A)
            A.wait_for_function("(id) => state.cards[id] && state.cards[id].b === 0", arg=u2, timeout=10000)
            check(True, "at start, A takes what B did meanwhile")
            A.evaluate(FREEZE)

            # ------------------------------------------------------------ a newer version of the app on the server
            print("== version plus récente")
            d = server_doc(SURL, code)
            newer = dict(d["data"], fmt=99)
            vn = server_put(SURL, code, d["v"], newer)["v"]
            B.evaluate(GRADE, [u2, True])
            r = B.evaluate(SYNC)
            check(not r["ok"] and "version plus récente" in r["err"] and server_doc(SURL, code)["data"]["fmt"] == 99,
                  "a document of a newer app: refused, not overwritten", r)
            server_put(SURL, code, vn, d["data"])
            check(B.evaluate(SYNC)["ok"], "with the document back to this version, B syncs again")
            A.evaluate(SYNC)

            # ------------------------------------------------------------ the server's copies
            print("== copies du serveur")
            A.click(".tab[data-view='settings']")
            A.click("[data-sync='copies']")
            A.wait_for_function("() => !document.querySelector('#copies-list').textContent.includes('Chargement')")
            n = A.evaluate("() => document.querySelectorAll('#copies-list [data-copy]').length")
            check(n == 1, "one copy so far: version 1, kept when it was first replaced", n)
            shot(A, "sync-04-copies")
            A.click("#copies-list [data-copy]")
            A.click("[data-copy-yes]")
            A.wait_for_function("() => document.querySelector('#toast').textContent.includes('Copie reprise')")
            A.evaluate(FREEZE)
            B.evaluate(SYNC)
            back_a, back_b = A.evaluate(CARDS, a3 + [x, y, u2]), B.evaluate(CARDS, a3 + [x, y, u2])
            check(back_a == back_b and back_a[a3[0]] == cards_a[a3[0]] and back_a[y] is None and back_a[u2] is None,
                  "copy taken back: both devices return to version 1", back_a)

            # ------------------------------------------------------------ stop, install
            print("== arrêter, installer")
            B.click(".tab[data-view='settings']")
            B.evaluate("() => renderSettings()")
            B.click("[data-sync='stop']")
            B.click("[data-sync='stop-yes']")
            check(B.evaluate("() => !syncCfg() && !localStorage.getItem('xingyinyi.sync-base')") and B.evaluate(CARDS, a3) == cards_a and
                  B.is_visible("#sync-code"), "stop on B: no code any more, its progress stays")
            B.fill("#sync-code", "Personne N’a Ce Code 42")
            B.click("[data-sync='join']")
            B.wait_for_selector("[data-sync='join-new']")
            check("Aucun appareil" in nb(B.text_content("#sync-err")) and B.evaluate("() => !syncCfg()"),
                  "a code typed that no device uses: asked first (a typo would make a second shared progress)", B.text_content("#sync-err"))
            B.click("[data-sync='join-new']")
            B.wait_for_function("() => { const c = syncCfg(); return c && c.at > 0; }")
            check(server_doc(SURL, "personnenacecode42")["v"] > 0, "« Créer ce code »: created")
            check(B.is_hidden("#install-row"), "no install button without the browser's offer")
            B.evaluate("""() => { window.__prompted = 0; const e = new Event('beforeinstallprompt', { cancelable: true });
                e.prompt = async () => { window.__prompted++; }; e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }""")
            check(B.is_visible("#install-row"), "Edge or Chrome offers to install: « Installer sur cet ordinateur »")
            shot(B, "sync-05-installer")
            B.click("#app-install")
            B.wait_for_timeout(100)
            check(B.evaluate("() => window.__prompted") == 1 and B.is_hidden("#install-row"), "Installer: the browser's own dialog, then the button goes")
            card_w = B.evaluate("() => { showView('study'); prism.layout(); return prism.w; }")
            check(card_w >= 540, "a larger card on a computer screen", card_w)
            A.emulate_media(color_scheme="dark")
            A.evaluate("() => { showView('settings'); document.querySelector('#sync-box').scrollIntoView(); }")
            shot(A, "sync-06-sombre")
            browser.close()
    finally:
        srv.terminate()
        httpd_a.shutdown()
        httpd_b.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
