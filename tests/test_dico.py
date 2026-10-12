# -*- coding: utf-8 -*-
"""Dictionnaire et listes : un mot n'apparaît qu'une fois et appartient à toutes ses listes.

Site de test : Perso (liste du dépôt modifiable : un mot à elle, deux renvois), HSK 1 (2.0) (figée, 150 mots),
HSK 1 (3.0) (figée, inactive et masquée : renvois par caractères, par pinyin, par identifiant, un renvoi introuvable,
un mot défini, un homographe), Grande (figée, 400 mots, masquée) et un fichier de dictionnaire (un mot sans liste).
Vérifie : le dictionnaire et les listes d'un mot, la file et le test complet sans doublon, Mots › Toutes (listes
affichées, mots sans liste, recherche dans tout le dictionnaire, affichage par paquets), les deux interrupteurs de
Réglages, les listes figées, l'ajout d'un mot HSK à une liste, le formulaire qui propose le mot existant, le partage
d'une liste et son import, le mot du téléphone rattaché au mot HSK identique, le cache des listes, la publication des
changements d'une liste du dépôt (renvoi ajouté, renvoi retiré, mot défini retiré de sa liste : hors_liste).
Lancer depuis la racine du dépôt :  py tests\\test_dico.py
"""
import json
import os
import re

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, nb

CHARS = "山水火木金土日月风雨花草鸟鱼马牛羊米石田"


def site_dico(name):
    site = fresh_copy(name)
    decks = os.path.join(site, "decks")
    cfg = {"listes": [
        {"id": "perso", "nom": "Perso", "fichier": "perso.tsv", "actif": True},
        {"id": "hsk1", "nom": "HSK 1 (2.0)", "fichier": "hsk1.tsv", "actif": True, "fixe": True},
        {"id": "hsk30-1", "nom": "HSK 1 (3.0)", "fichier": "hsk30-1.tsv", "actif": False, "afficher": False, "fixe": True},
        {"id": "big", "nom": "Grande", "fichier": "big.tsv", "actif": False, "afficher": False, "fixe": True},
        {"id": "mots", "nom": "Mots sans liste", "fichier": "mots.tsv", "dictionnaire": True}]}
    with open(os.path.join(decks, "decks.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    files = {
        "perso.tsv": "hanzi\tpinyin\tfrancais\n打印\tdǎyìn\timprimer\n爱\n你好\n",
        "hsk30-1.tsv": "# renvois et définitions\nhanzi\tpinyin\tfrancais\n爱\n点\tdiǎn\nhsk1:电脑\n不存在\n你好\tnǐ hǎo\tbonjour\n"
                       "点\tdiǎn\tcommander (un plat)\n爱\n",
        "mots.tsv": "hanzi\tpinyin\tfrancais\n词典\tcídiǎn\tdictionnaire\n",
        "big.tsv": "hanzi\tpinyin\tfrancais\n" + "".join("%s%s\tshān\tmot %d\n" % (a, b, i * 20 + j)
                                                      for i, a in enumerate(CHARS) for j, b in enumerate(CHARS)),
    }
    for f, text in files.items():
        with open(os.path.join(decks, f), "w", encoding="utf-8") as fh:
            fh.write(text)
    return site


def wcount(page):
    return int(re.match(r"\d+", nb(page.inner_text("#wcount"))).group(0))


def view(page, name):
    page.click('.tab[data-view="%s"]' % name)
    page.wait_for_timeout(250)


MOCK_GH = """() => {
  window.__calls = [];
  localStorage.setItem('xingyinyi.github', JSON.stringify({ repo: 'u/r', token: 't' }));
  gh = async (path, opts = {}) => {
    __calls.push([opts.method || 'GET', path, opts.body ? JSON.stringify(opts.body) : '']);
    if (path === '/repos/u/r') return { default_branch: 'main', permissions: { push: true } };
    if (path.includes('/git/ref/heads/')) return { object: { sha: 'c0' } };
    if (path.includes('/git/commits/')) return { tree: { sha: 't0' } };
    if (path.includes('/contents/')) {
      const f = decodeURIComponent(path.split('/contents/')[1].split('?')[0]);
      const r = await fetch(f, { cache: 'no-store' });
      if (!r.ok) throw Object.assign(new Error('absent'), { status: 404 });
      return r.text();
    }
    if (path.endsWith('/git/trees')) return { sha: 't1' };
    if (path.endsWith('/git/commits')) return { sha: 'c1' };
    return {};
  };
}"""


def main():
    errors = []
    site = site_dico("site-dico")
    httpd, url = serve(site)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = new_page(browser, errors)
        page.goto(url)
        wait_ready(page)

        # ------------------------------------------------------------ the dictionary and the lists of a word
        d = page.evaluate("""() => ({ n: DECK.length, uniq: new Set(DECK.map(w => w.id)).size,
            ai: BYID.get('hsk1:爱').lists, n3: LISTBYID.get('hsk30-1').words.map(w => w.id),
            free: DECK.filter(w => !w.lists.length).map(w => w.id), lists: LISTS.map(L => L.id) })""")
        check(d["n"] == 554 and d["uniq"] == 554, "dictionary: every word once (1 + 150 + 2 + 400 + 1)", d["n"])
        check(d["lists"] == ["tel", "perso", "hsk1", "hsk30-1", "big"], "lists: the phone first, then decks.json (the dictionary file is no list)", d["lists"])
        check(d["ai"] == ["perso", "hsk1", "hsk30-1"], "爱 belongs to its three lists", d["ai"])
        check(d["n3"] == ["hsk1:爱", "hsk1:点", "hsk1:电脑", "hsk30-1:你好", "hsk30-1:点"],
              "pointers by characters, by pinyin (the HSK word first), by id; unknown one left out; no word twice", d["n3"])
        check(d["free"] == ["mots:词典"], "the dictionary file: a word of no list", d["free"])

        # ------------------------------------------------------------ the line and the full test: each word once
        page.evaluate("() => { state.decks['hsk30-1'].on = true; save(); afterDeckChange(); }")
        ln = page.evaluate("() => { const q = lineOf(dayNum()); return { n: q.length, uniq: new Set(q).size, head: q.slice(0, 3) }; }")
        check(ln["n"] == ln["uniq"] == 1 + 150 + 2 + 0 and ln["head"] == ["perso:打印", "hsk1:爱", "hsk30-1:你好"],
              "line: the active lists in order, a word of several lists once", ln)
        n = page.evaluate("() => { study.startTest(['perso', 'hsk30-1']); const n = state.test.n; state.test = null; study.build(); return n; }")
        check(n == 6, "full test of two lists: their words once each", n)
        page.evaluate("() => { state.decks['hsk30-1'].on = false; save(); afterDeckChange(); }")

        # ------------------------------------------------------------ Mots › Toutes, Afficher, Sans liste
        view(page, "words")
        check(wcount(page) == 153, "Toutes: the words of the lists shown (Perso, HSK 1) and of no list, once each", wcount(page))
        dk = page.evaluate("() => [...document.querySelectorAll('.wrow')].find(r => r.dataset.id === 'hsk1:爱').querySelector('.dk').textContent")
        check(nb(dk) == "Perso +2", "a row says its first list shown, and how many others", dk)
        view(page, "settings")
        rows = page.evaluate("""() => ({ deck: document.querySelectorAll('#deck-settings .switch[data-deck]').length,
            show: document.querySelectorAll('#deck-settings .switch[data-show]').length,
            free: !!document.querySelector('#deck-settings .switch[data-show="sans"]'),
            fixed: [...document.querySelectorAll('#deck-settings .set small')].filter(s => s.textContent.includes('liste figée')).length })""")
        check(rows == {"deck": 4, "show": 5, "free": True, "fixed": 3}, "Réglages: Réviser and Afficher for each list, Afficher for the words of no list", rows)
        groups = page.evaluate("""() => { const out = [];
            for (const el of document.querySelector('#deck-settings').children) {
                if (el.matches('h3.deck-group')) out.push([el.textContent, []]);
                const sw = el.querySelector('.switch[data-show]');
                if (sw && out.length) out[out.length - 1][1].push(sw.dataset.show);
            }
            return out; }""")
        check(groups == [["HSK 2.0", ["hsk1"]], ["HSK 3.0", ["hsk30-1"]], ["Autres listes", ["big"]], ["Mes listes", ["perso", "sans"]]],
              "Réglages: the lists in groups, HSK 2.0, HSK 3.0, other fixed lists, then the user's lists and the words of no list", groups)
        lv = page.evaluate("""() => { const L = n => ({ id: 'hsk' + n, nom: 'HSK ' + n + ' (2.0)', fixe: true });
            return [listGroup({ id: 'hsk30-4', nom: 'HSK 4 (3.0)', fixe: true }), listGroup(L(5)), listGroup({ id: 'p-x', nom: 'Cours', phone: true }),
                    listGroup({ id: 'perso', nom: 'Perso' }), listGroup({ id: 'x', nom: 'HSK 6 (3.0)', fixe: true })]; }""")
        check(lv == ["hsk3", "hsk2", "mine", "mine", "hsk3"], "listGroup: by id, else by the name of the list", lv)
        page.click('#deck-settings .switch[data-show="hsk30-1"]')
        page.click('#deck-settings .switch[data-show="sans"]')
        shot(page, "dico-01-settings")
        view(page, "words")
        check(wcount(page) == 153, "Afficher: HSK 1 (3.0) shown (+点 commander), the words of no list hidden (−词典)", wcount(page))
        page.click('#wdeck button[data-deck="sans"]')
        page.wait_for_timeout(150)
        check(wcount(page) == 1 and page.locator(".wrow").count() == 1, "tab Sans liste", wcount(page))
        page.click('#wdeck button[data-deck="all"]')
        page.fill("#q", "山")
        page.wait_for_timeout(250)
        check(wcount(page) == 39, "a search goes through the whole dictionary, the lists hidden too", wcount(page))
        page.fill("#q", "")
        # rows a few at a time
        page.click('#wdeck button[data-deck="big"]')
        page.wait_for_timeout(200)
        first = page.locator(".wrow").count()
        page.click("#wlist [data-more]")
        page.wait_for_timeout(200)
        check(wcount(page) == 400 and first == 150 and page.locator(".wrow").count() == 400, "a long list: 150 rows, then the rest", (first, page.locator(".wrow").count()))
        check("liste figée" in nb(page.inner_text("#wcount")) and page.is_hidden("#listbar"), "a fixed list: no bar to add or share", page.inner_text("#wcount"))
        page.click('#wdeck button[data-deck="perso"]')
        page.wait_for_timeout(150)
        check(page.is_visible('#listbar [data-la="add"]') and page.is_visible('#listbar [data-la="share"]'), "a list of decks/ that can change: add and share")

        # ------------------------------------------------------------ a word of HSK in a list of the phone and of decks/
        page.click('.wrow[data-id="hsk1:电脑"]') if page.locator('.wrow[data-id="hsk1:电脑"]').count() else None
        page.evaluate("() => wordSheet('hsk1:电脑')")
        page.wait_for_selector("#sheet:not([hidden])")
        page.click('#sheet [data-act="lists"]')
        sws = page.evaluate("() => [...document.querySelectorAll('#sheet [data-inl]')].map(b => [b.dataset.inl, b.getAttribute('aria-checked')])")
        check(sws == [["tel", "false"], ["perso", "false"]], "Listes…: the lists the phone may change (not the HSK ones)", sws)
        page.click('#sheet [data-inl="perso"]')
        page.click('#sheet [data-inl="tel"]')
        st = page.evaluate("() => ({ e: state.listEdits, tel: state.tel, perso: LISTBYID.get('perso').words.map(w => w.id), lists: BYID.get('hsk1:电脑').lists, n: pendingCount() })")
        check(st["e"] == {"perso": {"add": ["hsk1:电脑"], "del": []}} and st["tel"] == ["hsk1:电脑"] and st["perso"][-1] == "hsk1:电脑"
              and st["lists"] == ["tel", "perso", "hsk1", "hsk30-1"] and st["n"] == 2,
              "a word of HSK added to Perso (kept on the phone until published) and to Ajoutés ici", st)
        page.click("#sheet .close")
        # the form: a word of the dictionary is offered, never written twice
        page.click("#btn-add")
        page.fill("#f-h", "你")
        page.wait_for_timeout(100)
        check("Déjà dans le dictionnaire" in nb(page.inner_text("#f-hh")) and page.locator("#f-hh [data-take]").count() == 1,
              "form: the word of the dictionary offered to the list", page.inner_text("#f-hh"))
        page.click("#f-hh [data-take]")
        page.wait_for_timeout(150)
        check(page.evaluate("() => state.listEdits.perso.add.includes('hsk1:你')"), "form: 你 added to Perso (the list open), not written again")
        page.click("#btn-add")
        page.fill("#f-h", "打印")
        page.fill("#f-p", "da3yin4")
        page.fill("#f-f", "imprimer")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        check("déjà dans le dictionnaire (Perso)" in nb(page.inner_text("#f-err")), "form: the same word refused", page.inner_text("#f-err"))
        page.click("#sheet .close")

        # ------------------------------------------------------------ sharing a list, then importing it elsewhere
        page.evaluate("() => { state.listEdits = {}; save(); rebuildDeck(); }")
        text = page.evaluate("() => listFileText(LISTBYID.get('perso'))")
        lines = text.strip().split("\n")
        check(lines[0].startswith("# 形音义 : liste « Perso »") and lines[1].startswith("hanzi\tpinyin\tfrancais")
              and lines[2:] == ["打印\tdǎyìn\timprimer", "爱", "你好"],
              "shared list: its header, a full line for a word not in HSK, a pointer for the others", lines)
        check(len(text.encode("utf-8")) < 270, "shared list: a small file", len(text.encode("utf-8")))
        ctx2, page2 = new_page(browser, errors)
        page2.goto(url)
        wait_ready(page2)
        page2.click('.tab[data-view="words"]')
        page2.click("#btn-import")
        page2.fill("#imp-t", text + "新词\txīncí\tnouveau mot\n")
        page2.wait_for_timeout(150)
        info = nb(page2.inner_text("#imp-info"))
        page2.click("#imp-go")
        page2.wait_for_timeout(300)
        im = page2.evaluate("() => ({ lists: state.lists.map(x => [x.nom, x.ids]), custom: state.custom.map(w => w.h), toast: document.querySelector('#toast').textContent })")
        check(info.startswith("Liste partagée « Perso », 4 mots") and len(im["lists"]) == 1 and im["lists"][0][0] == "Perso (2)"
              and im["lists"][0][1][:3] == ["perso:打印", "hsk1:爱", "hsk30-1:你好"] and im["custom"] == ["新词"],
              "import: a new list; the words this phone has are reused, the new one joins the dictionary", (info, im))
        ctx2.close()

        # ------------------------------------------------------------ a word of the phone that HSK has too: one word
        ctx3, page3 = new_page(browser, errors)
        page3.goto(url)
        wait_ready(page3)
        page3.evaluate("""() => { const s = JSON.parse(localStorage.getItem('xingyinyi.v2'));
            s.custom = [{ id: 'u-x1', h: '电脑', p: 'diàn nǎo', f: 'ordi' }]; s.tel = ['u-x1'];
            s.cards = { 'u-x1': { b: 2, d: dayNum() + 3, t: dayNum() - 1, s: dayNum() - 9, r: 3, l: 0, kn: 1 } };
            localStorage.setItem('xingyinyi.v2', JSON.stringify(s)); }""")
        page3.reload()
        wait_ready(page3)
        fo = page3.evaluate("() => ({ custom: state.custom.length, tel: state.tel, card: state.cards['hsk1:电脑'], old: state.cards['u-x1'] || null })")
        check(fo["custom"] == 0 and fo["tel"] == ["hsk1:电脑"] and fo["card"] and fo["card"]["b"] == 2 and fo["old"] is None,
              "a phone word with the characters and pinyin of an HSK word becomes that word, with its progress", fo)
        cache = page3.evaluate("""async () => { const r = await (await caches.open('listes-xingyinyi')).match('__listes__.json');
            return { cached: !!r && Object.keys((await r.json()).texts).length, local: localStorage.getItem('xingyinyi.listes') }; }""")
        check(cache == {"cached": 5, "local": None}, "lists cached in Cache Storage, not in localStorage", cache)
        ctx3.close()

        # ------------------------------------------------------------ publishing the changes of a list of decks/
        page.evaluate(MOCK_GH)
        page.evaluate("""() => { state.tel = []; state.lists = [];
            state.listEdits = { perso: { add: ['hsk1:电脑'], del: ['hsk1:爱', 'perso:打印'] } }; save(); rebuildDeck(); }""")
        page.evaluate("() => publishGitHub()")
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('Publié')", timeout=8000)
        tree = page.evaluate("() => JSON.parse(__calls.find(c => c[1].endsWith('/git/trees'))[2])")
        files = {e["path"]: e.get("content") for e in tree["tree"]}
        body = files.get("decks/perso.tsv", "")
        bl = body.strip().split("\n")
        check(bl[0] == "hanzi\tpinyin\tfrancais\thors_liste" and "打印\tdǎyìn\timprimer\tx" in bl and "爱" not in bl and bl[-1] == "电脑",
              "publication: pointer added, pointer removed, a word defined here taken out of the list (hors_liste)", bl)
        after = page.evaluate("() => ({ e: state.listEdits, perso: LISTBYID.get('perso').words.map(w => w.id), free: BYID.get('perso:打印').lists })")
        check(after == {"e": {}, "perso": ["hsk30-1:你好", "hsk1:电脑"], "free": []}, "after publication: the list as published, 打印 still in the dictionary", after)
        ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check(ov == 0, "no horizontal overflow", ov)

        # ------------------------------------------------------------ a phone word in two lists: written once
        page.evaluate("""() => { __calls.length = 0; state.listEdits = {};
            state.custom = [{ id: 'u-n1', h: '新词', p: 'xīncí', f: 'mot nouveau' }]; state.tel = [];
            state.lists = [{ id: 'p-a', nom: 'Alpha', ids: ['u-n1'] }, { id: 'p-b', nom: 'Beta', ids: ['u-n1', 'hsk1:爱'] }];
            save(); rebuildDeck(); }""")
        page.evaluate("() => publishGitHub()")
        page.wait_for_function("() => __calls.some(c => c[1].includes('/git/refs/heads/')) && !publishing", timeout=8000)
        tree = page.evaluate("() => JSON.parse(__calls.find(c => c[1].endsWith('/git/trees'))[2])")
        files = {e["path"]: e.get("content") or "" for e in tree["tree"]}
        a, b = files.get("decks/alpha.tsv", ""), files.get("decks/beta.tsv", "")
        check("新词\txīncí\tmot nouveau" in a and b.strip().split("\n")[-2:] == ["alpha:新词", "爱"] and "xīncí" not in b,
              "publication: a phone word of two lists defined once, the other list points to it", (a[-60:], b[-40:]))
        page.evaluate("() => { state.lists = []; state.custom = []; save(); rebuildDeck(); }")

        # ------------------------------------------------------------ a word of the file marked hors_liste comes back
        perso = os.path.join(site, "decks", "perso.tsv")
        with open(perso, encoding="utf-8") as fh:
            keep = fh.read()
        with open(perso, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("hanzi\tpinyin\tfrancais\thors_liste\n打印\tdǎyìn\timprimer\tx\n你好\n")
        page.evaluate("() => { __calls.length = 0; state.listEdits = { perso: { add: ['perso:打印'], del: [] } }; save(); }")
        page.evaluate("() => publishGitHub()")
        page.wait_for_function("() => __calls.some(c => c[1].includes('/git/refs/heads/')) && !publishing", timeout=8000)
        tree = page.evaluate("() => JSON.parse(__calls.find(c => c[1].endsWith('/git/trees'))[2])")
        body = {e["path"]: e.get("content") for e in tree["tree"]}.get("decks/perso.tsv", "")
        check(body.strip().split("\n") == ["hanzi\tpinyin\tfrancais\thors_liste", "打印\tdǎyìn\timprimer", "你好"],
              "publication: a word marked hors_liste put back in its list loses its x, no second line", body)
        with open(perso, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(keep)
        page.evaluate("() => { state.listEdits = {}; save(); rebuildDeck(); }")

        # ------------------------------------------------------------ the reading decides, not the characters alone
        page.evaluate("""() => { state.custom = [{ id: 'u-d1', h: '打印', p: 'dàyìn', f: 'autre sens' }]; state.tel = ['u-d1'];
            state.cards['u-d1'] = { b: 2, d: dayNum() + 2, t: dayNum() - 1, s: dayNum() - 5, r: 4, l: 0, kn: 1 };
            save(); rebuildDeck(); mergeTel(); }""")
        mt = page.evaluate("() => ({ custom: state.custom.map(w => w.id), tel: state.tel, card: !!state.cards['u-d1'], ref: refText(BYID.get('perso:打印')) })")
        check(mt == {"custom": ["u-d1"], "tel": ["u-d1"], "card": True, "ref": "打印\tdǎyìn"},
              "a phone word of the same characters but another reading stays itself; pointers then name the reading", mt)
        page.evaluate("() => { state.custom = []; state.tel = []; delete state.cards['u-d1']; save(); rebuildDeck(); }")
        # editing: the voice text stays, the pinyin typed in digits is the same pinyin
        page.evaluate("() => editSheet('hsk1:的')")
        page.fill("#f-n", "note du téléphone")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        page.evaluate("() => editSheet('hsk1:爱')")
        page.fill("#f-p", "ai4")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        ed = page.evaluate("() => ({ de: state.edits['hsk1:的'], s: BYID.get('hsk1:的').s, ai: state.edits['hsk1:爱'] || null })")
        check(ed == {"de": {"n": "note du téléphone"}, "s": "我的", "ai": None},
              "a correction keeps the voice text; a pinyin typed in digits that is the same is no correction", ed)
        page.evaluate("() => { state.edits = {}; state.custom = [{ id: 'u-s1', h: '新词', p: 'xīncí', f: 'mot', s: '新词语' }]; save(); rebuildDeck(); editSheet('u-s1'); }")
        page.fill("#f-f", "mot nouveau")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        ed = page.evaluate("() => { const { m, ...w } = state.custom[0]; return { w, m: m > Date.now() - 60000 }; }")
        check(ed == {"w": {"id": "u-s1", "h": "新词", "p": "xīncí", "f": "mot nouveau", "s": "新词语"}, "m": True},
              "a phone word edited keeps its voice text, and the time of the correction", ed)
        # a phone word that doubles an HSK word (older version) can still be corrected
        page.evaluate("() => { state.custom = [{ id: 'u-p1', h: '点', p: 'diǎn', f: 'commandre' }]; save(); rebuildDeck(); editSheet('u-p1'); }")
        page.fill("#f-f", "commander (un plat)")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        check(page.evaluate("() => state.custom[0].f") == "commander (un plat)", "an old phone word that doubles an HSK word can be corrected")
        page.evaluate("() => { state.custom = []; save(); rebuildDeck(); afterDeckChange(); }")

        # ------------------------------------------------------------ the form: a new list for a word of the dictionary
        page.click("#btn-add")
        page.select_option("#f-l", "__new")
        page.fill("#f-ln", "Révisions")
        page.fill("#f-h", "你")
        page.wait_for_timeout(100)
        page.click("#f-hh [data-take]")
        page.wait_for_timeout(150)
        nl = page.evaluate("() => state.lists.map(x => [x.nom, x.ids])")
        check(nl == [["Révisions", ["hsk1:你"]]], "form: a new list made for a word of the dictionary", nl)
        page.evaluate("() => { state.lists = []; save(); rebuildDeck(); afterDeckChange(); }")
        gone = page.evaluate("() => { const d = document.createElement('div'); d.innerHTML = formHTML({ target: 'p-gone' }); return d.querySelector('#f-l').value; }")
        check(gone == "tel", "form: a list gone falls back to Ajoutés ici", gone)
        page.click("#btn-add")
        page.fill("#f-h", "你")
        page.fill("#f-p", "nǐ")
        page.fill("#f-f", "toi")
        page.select_option("#f-l", "")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(150)
        err = page.inner_text("#f-err")
        check("rien à ajouter" in nb(err) and "\u202f:" in err, "form: no list chosen, the word is there already (and the typography)", err)
        page.click("#sheet .close")

        # ------------------------------------------------------------ import: homographs and other notations
        imp = page.evaluate("""() => ({
            dian: bestSame('点', 'diǎn', 'commander (un plat)'), heure: bestSame('点', 'diǎn', 'heure'),
            loose: (bestSame('朋友', 'péngyǒu', 'ami').w || {}).id, other: bestSame('东西', 'dōngxī', 'est et ouest').w,
            strict: (sameWords('朋友', 'péngyǒu')[0] || {}).id || null, yi: (sameWords('爱', 'āi')[0] || {}).id || null,
            yidian: (sameWords('一点儿', 'yīdiǎnr')[0] || {}).id || null,
            er: [pyKey('na3r') === pyKey('nǎr'), pinyinText('yi2hui4r5'), pinyinText('Ni3 qu4 na3r?'), (sameWords('哪儿', 'na3r')[0] || {}).id || null],
            head: parseTSV('汉字\\n打印\\tdǎyìn\\timprimer').map(r => r.h) })""")
        check(imp["dian"]["w"]["id"] == "hsk30-1:点" and not imp["dian"]["amb"] and imp["heure"]["w"]["id"] == "hsk1:点",
              "import: among homographs, the one of this sense", (imp["dian"]["w"]["id"], imp["heure"]["w"]["id"]))
        check(imp["loose"] == "hsk1:朋友" and imp["strict"] is None and imp["other"] is None and imp["yi"] is None,
              "a tone noted for a neutral tone: the same word only with the same sense (朋友 ami; 东西 dōngxī « est et ouest » is another word)", imp)
        check(imp["yidian"] == "hsk1:一点儿" and imp["er"] == [True, "yíhuìr", "Nǐ qù nǎr?", "hsk1:哪儿"],
              "一 noted with its own tone is the same reading; 儿 in digits (na3r = nǎr)", imp)
        check(imp["head"] == ["汉字", "打印"], "a file that starts with the word 汉字: a word, not a header", imp["head"])

        # the import sheet: another word is created (pinyin written with accents), the same words are taken
        page.evaluate("() => { state.custom = []; state.tel = []; wdeck = 'all'; save(); rebuildDeck(); afterDeckChange(); importSheet(); }")
        page.fill("#imp-t", "东西 ; dong1xi1 ; est et ouest\n哪儿 ; na3r ; où\n朋友 ; péngyǒu ; ami")
        page.wait_for_timeout(100)
        info = nb(page.inner_text("#imp-info"))
        page.click("#imp-go")
        page.wait_for_timeout(150)
        got = page.evaluate("() => ({ custom: state.custom.map(w => [w.h, w.p, w.f]), tel: state.tel.map(id => id.startsWith('u-') ? 'u' : id) })")
        check(info.startswith("3 mots à ajouter") and got == {"custom": [["东西", "dōngxī", "est et ouest"]], "tel": ["u", "hsk1:哪儿", "hsk1:朋友"]},
              "import: 东西 dōngxī is a new word; 哪儿 na3r and 朋友 péngyǒu « ami » are the HSK words", (info, got))
        # the form: 东西 dōngxī « est et ouest » can be written, 朋友 péngyǒu « ami » is the word of the dictionary
        page.evaluate("() => { state.custom = []; state.tel = []; save(); rebuildDeck(); afterDeckChange(); }")
        for h, py, fr in (("东西", "dōngxī", "est et ouest"), ("朋友", "péngyǒu", "ami")):
            page.click("#btn-add")
            page.fill("#f-h", h)
            page.fill("#f-p", py)
            page.fill("#f-f", fr)
            page.select_option("#f-l", "tel")
            page.click("#wform button[type=submit]")
            page.wait_for_timeout(150)
        err = nb(page.inner_text("#f-err"))
        page.click("#sheet .close")
        made = page.evaluate("() => state.custom.map(w => [w.h, w.p])")
        check(made == [["东西", "dōngxī"]] and "« 朋友 » péngyou est déjà dans le dictionnaire" in err,
              "form: another word of the same characters is written; the same word noted otherwise is refused", (made, err))
        # words of the phone saved by an older import, pinyin in digits
        mig = page.evaluate("""() => normalizeState({ v: 2, sched: 1, settings: {}, cards: {},
            custom: [{ id: 'u-m1', h: '哪儿', p: 'na3r', f: 'où', e: '你去哪儿？', ep: 'Ni3 qu4 na3r?' }], tel: ['u-m1'] }).custom[0]""")
        check(mig["p"] == "nǎr" and mig["ep"] == "Nǐ qù nǎr?", "an older word of the phone: its pinyin in digits is written with accents", mig)
        page.evaluate("() => { state.custom = []; state.tel = []; save(); rebuildDeck(); afterDeckChange(); }")

        # ------------------------------------------------------------ corrections of an older version: no empty voice text
        old = page.evaluate("""() => ({ e: normalizeState({ v: 2, sched: 1, settings: {}, cards: {},
            edits: { 'hsk1:的': { n: 'x', s: '' }, 'hsk1:爱': { s: '' } } }).edits,
            a: applyEdit('的\\tde\\tparticule\\t\\t我的', '的', { s: '', n: 'note' }) })""")
        check(old == {"e": {"hsk1:的": {"n": "x"}}, "a": "的\tde\tparticule\tnote\t我的"},
              "a correction with an empty voice text (older version): the voice text of the file stays", old)

        # ------------------------------------------------------------ the guard after a publication
        g = page.evaluate("""() => {
            const cfgA = { listes: [{ id: 'a' }] }, cfgB = { listes: [{ id: 'a' }, { id: 'b' }] }, out = {};
            const set = at => localStorage.setItem(PKEY, JSON.stringify({ at, files: { '': hashStr(JSON.stringify(cfgB)), 'b.tsv': hashStr('new') },
                old: [{ '': hashStr(JSON.stringify(cfgA)), 'b.tsv': '-' }] }));
            const late = Date.now() - 20 * 60e3;
            set(late); out.oldLate = stalePages({ config: cfgA, texts: {} }); out.kept = !!localStorage.getItem(PKEY);
            out.fresh = stalePages({ config: cfgB, texts: { 'b.tsv': 'new' } }); out.cleared = !localStorage.getItem(PKEY);
            set(Date.now()); out.otherSoon = stalePages({ config: cfgB, texts: { 'b.tsv': 'changed' } });
            set(late); out.otherLate = stalePages({ config: cfgB, texts: { 'b.tsv': 'changed' } });
            localStorage.removeItem(PKEY);
            return out; }""")
        check(g == {"oldLate": True, "kept": True, "fresh": False, "cleared": True, "otherSoon": True, "otherLate": False},
              "after a publication: the files of before are refused even after 15 minutes; the published ones lift the guard", g)

        # ------------------------------------------------------------ a file that does not arrive keeps the copy of before
        miss = page.evaluate("""async () => {
            const real = fetchLists, first = LISTBYID.get('big').words[0].id;
            fetchLists = async () => { const s = await real(); delete s.texts['big.tsv']; s.missing = ['big.tsv']; return s; };
            state.test = { lists: ['big'], n: 2, queue: [first, 'zz:gone'], ok: [], ko: [] };
            try { await refreshLists(false, true); } finally { fetchLists = real; }
            const c = await readCache();
            const out = { big: LISTBYID.get('big').words.length, cache: typeof c.texts['big.tsv'],
                toast: document.querySelector('#toast').textContent, q: testQueue(state.test) };
            state.test = { lists: ['big'], n: 1, queue: ['zz:gone'], ok: [], ko: [] };
            const L = BASE.find(x => x.id === 'big'); L.missing = true;
            out.waits = [testQueue(state.test).length, state.test.queue.length];
            L.missing = false;
            out.gone = [testQueue(state.test).length, state.test.queue.length];
            state.test = null; save();
            return out; }""")
        check(miss["big"] == 400 and miss["cache"] == "string" and "Fichier introuvable dans decks/" in nb(miss["toast"])
              and len(miss["q"]) == 1 and miss["waits"] == [0, 1] and miss["gone"] == [0, 0],
              "a file that did not arrive: its copy of before stays; a word of the test waits for its list, leaves once all are here", miss)

        # ------------------------------------------------------------ restore before the lists are loaded; ids that are no more
        rs = page.evaluate("""() => { const keep = state; listsReady = false;
            state = normalizeState({ v: 2, sched: 1, settings: {}, cards: {}, listEdits: { perso: { add: ['hsk1:你'], del: [] } } });
            mergeTel(); const out = JSON.stringify(state.listEdits); state = keep; listsReady = true; rebuildDeck(); return out; }""")
        check(rs == '{"perso":{"add":["hsk1:你"],"del":[]}}', "lists not loaded yet: the changes waiting for a publication stay", rs)
        gone = page.evaluate("""() => { state.lists = [{ id: 'p-d', nom: 'Divers', ids: ['hsk1:爱', 'zz:disparu'] }];
            state.listEdits = { perso: { add: ['zz:parti'], del: [] } }; save(); rebuildDeck();
            const n0 = pendingCount(); mergeTel();
            const out = { n0, ids: state.lists[0].ids, le: state.listEdits, n1: pendingCount() };
            state.lists = []; state.listEdits = {}; save(); rebuildDeck(); return out; }""")
        check(gone == {"n0": 1, "ids": ["hsk1:爱"], "le": {}, "n1": 1}, "an id that is no more: not waiting for a publication, and dropped", gone)

        # ------------------------------------------------------------ copy for the computer: a word of two lists written once
        ex = page.evaluate("""() => { state.custom = [{ id: 'u-e1', h: '新词', p: 'xīncí', f: 'mot nouveau' }]; const inP = [...LISTBYID.get('perso').fileIds][0]; state.tel = ['u-e1', inP];
            state.lists = [{ id: 'p-c', nom: 'Cours', ids: ['u-e1', 'hsk1:你'] }]; state.sent = {}; save(); rebuildDeck();
            const r = exportRows(); exportSheet();
            return { tel: r.get('tel').rows, cours: r.get('p-c').rows, sent: state.sent, c: typeof state.custom[0].c }; }""")
        page.click("#sheet .close")
        check(ex == {"tel": ["新词\txīncí\tmot nouveau"], "cours": ["新词", "你"], "sent": {"tel": ["u-e1"], "p-c": ["u-e1", "hsk1:你"]}, "c": "number"},
              "copy for the computer: a phone word in full once, a pointer in the other list, not a word Perso has", ex)
        page.evaluate("() => { state.custom = []; state.tel = []; state.lists = []; state.sent = {}; save(); rebuildDeck(); afterDeckChange(); }")

        # ------------------------------------------------------------ the lines arrive: corrections made after the copy stay
        mg = page.evaluate("""async () => {
            const before = await readCache();
            state.custom = [{ id: 'u-k1', h: '新词', p: 'xīncí', f: 'sens corrigé', c: 1000, m: 2000 },
                            { id: 'u-k2', h: '旧词', p: 'jiùcí', f: 'mot', c: 3000, m: 2000 },
                            { id: 'u-k3', h: '打印', p: 'dǎyin', f: 'imprimer (en couleurs)' }];
            const inP = [...LISTBYID.get('perso').fileIds][0];
            state.tel = ['u-k1', 'u-k2', 'u-k3', inP]; state.sent = { tel: ['u-k1', 'u-k2'] }; state.edits = {};
            save(); rebuildDeck();
            const src = JSON.parse(JSON.stringify(before));
            src.texts['perso.tsv'] = src.texts['perso.tsv'].replace(/\\s*$/, '\\n') + '新词\\txīncí\\tsens d’avant\\n旧词\\tjiùcí\\tmot du dépôt\\n';
            useLists(src, 'quiet');
            const out = { inP, custom: state.custom.map(w => w.id), tel: state.tel, sent: state.sent, e1: state.edits['perso:新词'] || null,
                e2: state.edits['perso:旧词'] || null, f1: BYID.get('perso:新词').f, pending: pendingCount() };
            state.custom = []; state.tel = []; state.edits = {}; state.sent = {}; useLists(before, 'quiet');
            return out; }""")
        check(mg["custom"] == ["u-k3"] and mg["e1"] == {"f": "sens corrigé"} and mg["e2"] is None and mg["f1"] == "sens corrigé",
              "a phone word whose line arrives: a correction made after the copy stays; the line wins otherwise; "
              "another sense of the same first word (打印 « imprimer (en couleurs) ») is another word", mg)
        check(mg["tel"] == ["u-k3", mg["inP"]] and mg["sent"] == {} and mg["pending"] == 2,
              "Ajoutés ici: the words sent and arrived leave it; a word added here though Perso has it stays and waits for nothing", mg)
        ctx.close()
        browser.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
