# -*- coding: utf-8 -*-
"""Séance de révision de bout en bout, en clair et en sombre : chargement des listes, pinyin, file des seaux
(premier tour de tous les mots des listes actives, dans l'ordre des listes ; √ au seau 1 pour un jour, × au
seau 0 et en fin de file ; « mode » et « parJour » de decks.json ignorés), phrase d'exemple, Progrès et Réglages
(7 seaux), mots ajoutés sur le téléphone, mise à jour des listes depuis l'ordinateur, reprise de la première
version et passage des boîtes aux seaux, démarrage hors ligne, bandeau de nouvelle version, petit écran, écran
d'ordinateur (menu à gauche, carte et réponses côte à côte, fiche du mot à côté de la liste, deux colonnes).
Les seaux en détail (jours qui passent, délais, évaluation, écran de fin) : test_seaux.py.
Lancer depuis la racine du dépôt :  py tests\\test_seance.py
"""
import json
import os
import re

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, answer, nb

COUNTS = "() => [...document.querySelectorAll('#counts .count')].map(s => [+s.querySelector('b').textContent, s.lastChild.textContent])"
RECT = "const r = s => document.querySelector(s).getBoundingClientRect();"   # in page.evaluate: r(selector), its box
BARS = "() => { " + RECT + " return { tabs: r('.tabs').top, main: r('#main').bottom, card: prism.w }; }"   # the menu below main: a phone
# the sheet and the list: rows marked, the word beside the list, the focus (on the marked row, in the sheet, elsewhere)
SHEET = """() => { const s = document.querySelector('#sheet'), row = document.querySelector('#wlist .wrow[aria-current]');
    return { marked: [...document.querySelectorAll('#wlist .wrow[aria-current]')].map(b => b.dataset.id), open: sheetWord, shown: !s.hidden,
             modal: s.querySelector('.panel').getAttribute('aria-modal'),
             focus: row && document.activeElement === row ? 'row' : s.contains(document.activeElement) ? 'sheet' : document.activeElement.tagName }; }"""
# boxes of the main parts of the page, to compare the light and dark layouts
LAYOUT = """() => [...document.querySelectorAll('.tabs, #main, #stage, #actions, #example, #sheet .panel')]
    .map(e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map(Math.round); })"""
DELAYS_OUT = ["1 j", "3 j", "1 sem.", "2 sem.", "1 mois", "2 mois"]

# progression enregistrée par une version à boîtes et quotas (v2 sans « sched »)
SEED_BOXES = """(() => {
  if (sessionStorage.getItem('seeded')) return;
  sessionStorage.setItem('seeded', '1');
  const d = new Date(Date.now() - 4 * 3600e3);
  const today = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5);
  localStorage.setItem('xingyinyi.v2', JSON.stringify({ v: 2,
    settings: { newPerDay: 15, startFace: 1, autoAudio: false, rate: 0.9, toneColors: true, exDetails: false, exOnForm: true, exam: '2026-11-29' },
    cards: {
      'hsk3:还': { b: 4, d: today + 5, r: 6, l: 1, t: today - 3, s: today - 30, f: today - 10 },
      'hsk3:啊': { b: 1, d: today, r: 1, l: 0, t: today - 1, s: today - 1 },
      'hsk2:就': { b: 6, d: today + 30, r: 3, l: 0, t: today - 20, s: today - 40 },
      'hsk1:的': { b: 2, d: today - 1, r: 2, l: 1, t: today - 3, s: today - 9, f: today - 9 } },
    edits: {}, custom: [], lists: [],
    decks: { hsk2: { on: true, cfgOn: true, perDay: 3, cfgPer: 3 }, hsk1: { on: true, cfgOn: true, perDay: 3, cfgPer: 3 } },
    log: {}, extra: null }));
})();"""
OLD_IDS = ["hsk3:还", "hsk3:啊", "hsk2:就", "hsk1:的"]


def wcount(page):
    """Number of words of the Mots tab (the rows come a few at a time)."""
    return int(re.match(r"\d+", nb(page.inner_text("#wcount"))).group(0))


def counts(page):
    return [[n, nb(t)] for n, t in page.evaluate(COUNTS)]


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ------------------------------------------------------------ main flow, light + dark
        for scheme in ("light", "dark"):
            print("== %s" % scheme)
            site = fresh_copy("site-" + scheme)
            httpd, url = serve(site)
            ctx, page = new_page(browser, errors, scheme)
            page.goto(url)
            wait_ready(page)
            shot(page, "%s-01-study" % scheme)
            start = page.evaluate("""() => {
              const line = [study.cur, ...study.queue];
              return {
                deck: DECK.length, line,
                same: JSON.stringify(line) === JSON.stringify(lineOf(dayNum())),
                order: JSON.stringify(line) === JSON.stringify(LISTS.filter(L => deckOn(L.id)).flatMap(L => L.words.map(w => w.id))),
                pass: line.every(inPass), cards: Object.keys(state.cards).length,
                cfg: LISTS.some(L => 'mode' in L || 'parJour' in L) || Object.values(state.decks).some(d => 'perDay' in d || 'cfgPer' in d),
                chips: [...document.querySelectorAll('#card-chip .chip')].map(c => c.textContent),
              };
            }""")
            line = start["line"]
            check(start["deck"] == 601 and len(line) == 601 and len(set(line)) == 601 and start["same"],
                  "%s: the line holds every word once (601)" % scheme, (start["deck"], len(line)))
            check(start["order"] and line[0] == "hsk3:还" and all(i.startswith("hsk3:") for i in line[:300])
                  and all(i.startswith("hsk2:") for i in line[300:451]) and all(i.startswith("hsk1:") for i in line[451:]),
                  "%s: first pass in list order (HSK 3, HSK 2, HSK 1), file order inside a list" % scheme, line[:3])
            check(start["pass"] and start["cards"] == 0, "%s: every word waits for the first pass" % scheme, start["cards"])
            check(not start["cfg"], "%s: mode and parJour of decks.json ignored" % scheme)
            check(counts(page) == [[601, "à voir"], [0, "à revoir"]], "%s: header counts" % scheme, counts(page))
            check(start["chips"] == ["Nouveau mot", "HSK 3"], "%s: chips of a word never seen" % scheme, start["chips"])
            if scheme == "light":
                logic = page.evaluate("""() => {
                  const cls = p => parsePinyin(p).filter(t => !t.sep).map(t => t.s + t.t).join(" ");
                  return {
                    lists: LISTS.map(L => [L.id, L.words.length]),
                    py: {
                      tushuguan: cls("túshūguǎn"), yihuir: cls("yíhuìr"), beijing: cls("Běijīng Dàxué"),
                      nver: cls("nǚ'ér"), xian: cls("xī'ān"), pengyou: cls("péngyou"), dayin: cls("dayin"),
                      de: cls("de"), sentence: cls("Wǒ míngtiān bǎ shū huán gěi nǐ."), numeric: pinyinText("ke3ai4 / yi2hui4r5"),
                      zhi: pinyinText("zhǐ / zhī"), lv: cls("lǜsè"), er: cls("èr"), tian: cls("Tiān'ānmén"),
                      xiansheng: cls("xiānsheng"), fangjian: cls("fángjiān"), num2: pinyinText("nv3er2"),
                    },
                    fold: [fold("túshūguǎn"), fold("lǜ")],
                    ex: (w => [w.e, w.ep, w.ef])(BYID.get("hsk3:还")),
                  };
                }""")
                print(json.dumps(logic["py"], ensure_ascii=False, indent=1))
                lists = {l[0]: l for l in logic["lists"]}
                check(lists["hsk3"][1] == 300 and lists["hsk2"][1] == 151 and lists["hsk1"][1] == 150 and lists["perso"][1] == 0,
                      "list sizes", logic["lists"])
                check([l[0] for l in logic["lists"]] == ["tel", "perso", "hsk3", "hsk2", "hsk1"], "phone list first, then decks.json order", logic["lists"])
                check(logic["py"]["tushuguan"] == "tú2 shū1 guǎn3", "syllables túshūguǎn", logic["py"]["tushuguan"])
                check(logic["py"]["yihuir"] == "yí2 huìr4", "erhua glued", logic["py"]["yihuir"])
                check(logic["py"]["pengyou"] == "péng2 you5", "neutral tone", logic["py"]["pengyou"])
                check(logic["py"]["dayin"] == "da0 yin0", "toneless input stays uncoloured", logic["py"]["dayin"])
                check(logic["py"]["xian"] == "xī1 ān1" and logic["py"]["tian"] == "Tiān1 ān1 mén2", "apostrophes", (logic["py"]["xian"], logic["py"]["tian"]))
                check(logic["py"]["xiansheng"] == "xiān1 sheng5" and logic["py"]["fangjian"] == "fáng2 jiān1", "n/ng boundaries")
                check(logic["py"]["numeric"] == "kě’ài / yíhuìr", "numeric pinyin", logic["py"]["numeric"])
                check(logic["py"]["num2"] == "nǚ’ér", "numeric ü + apostrophe", logic["py"]["num2"])
                check(len(logic["py"]["sentence"].split(" ")) == 8, "sentence pinyin split", logic["py"]["sentence"])
                check(logic["ex"][0] == "我明天把书还给你。", "example for 还", logic["ex"])

            # covered slip before turning
            cov = page.evaluate("() => !!document.querySelector('#example .ex.covered') || !!document.querySelector('#example .ex.empty')")
            check(cov, "%s: example covered before turning" % scheme)
            page.click("#stage")
            page.wait_for_timeout(700)
            shot(page, "%s-02-turned" % scheme)
            state = page.evaluate("() => ({covered: !!document.querySelector('#example .ex.covered'), grades: !document.querySelector('#grades').hidden, word: BYID.get(study.cur).h})")
            check(not state["covered"] and state["grades"], "%s: slip revealed and grades shown after turning" % scheme, state)
            hints = page.evaluate("() => [document.querySelector('#gi0').textContent, document.querySelector('#gi1').textContent]")
            check([nb(h) for h in hints] == ["seau 0, fin de file", "seau 1, 1 jour"], "%s: hints under × and √" % scheme, hints)
            if page.locator("#example [data-ex-toggle]").count():
                page.click("#example [data-ex-toggle]")
                page.wait_for_timeout(450)
                shot(page, "%s-03-example-open" % scheme)
                check(page.evaluate("() => document.querySelector('#example .ex').classList.contains('open') && state.settings.exDetails && !document.querySelector('#example .ex-py')"),
                      "%s: translation shown, the pinyin stays on the 音 face" % scheme)
                # grades still on screen?
                box = page.evaluate("() => { const g = document.querySelector('#grades').getBoundingClientRect(); const m = document.querySelector('#main').getBoundingClientRect(); return [g.bottom, m.bottom]; }")
                check(box[0] <= box[1] + 1, "%s: grade buttons visible with example open" % scheme, box)
            page.click("#stage")
            page.wait_for_timeout(700)
            shot(page, "%s-04-face3" % scheme)

            # the first answers of the first pass (601 words: the end of the line is tested in test_seaux.py)
            today = page.evaluate("() => dayNum()")
            pattern = [1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1]
            ups, misses, bad = [], [], []
            for k, g in enumerate(pattern):
                if k == 5:
                    page.wait_for_function("() => study.ready")
                    if page.is_visible("#turnbtn"):
                        page.click("#turnbtn")
                    page.wait_for_timeout(600)
                    shot(page, "%s-05-midsession" % scheme)
                cur = answer(page, g, key=k in (3, 4))           # keys 2 (√) and 1 (×) once each
                st = page.evaluate("(id) => ({ c: state.cards[id], b: bucketOf(id), missed: missed(id), pass: inPass(id), line: [study.cur, ...study.queue] })", cur)
                if g:
                    ups.append(cur)
                    if not (st["b"] == 1 and st["c"]["d"] == today + 1 and cur not in st["line"]):
                        bad.append(("√", cur, st["c"]))
                else:
                    misses.append(cur)
                    if not (st["b"] == 0 and st["missed"] and not st["pass"] and st["line"][-1] == cur and st["line"].count(cur) == 1):
                        bad.append(("×", cur, st["c"], st["line"][-3:]))
            check(not bad, "%s: √ -> bucket 1 due tomorrow, × -> bucket 0 at the end of the line" % scheme, bad)
            after = page.evaluate("() => ({ line: [study.cur, ...study.queue], log: state.log[dayNum()] })")
            check(after["line"][-3:] == misses and len(after["line"]) == 601 - len(ups),
                  "%s: missed words wait at the end, in the order they were missed" % scheme, after["line"][-3:])
            check(counts(page) == [[601 - len(pattern), "à voir"], [len(misses), "à revoir"]], "%s: header counts after 12 answers" % scheme, counts(page))
            lg = after["log"] or {}
            check(lg.get("n") == 12 and lg.get("p") == 12 and not lg.get("r"), "%s: day log (12 new words out of the first pass)" % scheme, lg)
            shot(page, "%s-06-line" % scheme)

            # words
            page.click('.tab[data-view="words"]')
            page.wait_for_timeout(300)
            shot(page, "%s-07-words" % scheme)
            page.fill("#q", "tushu")
            page.wait_for_timeout(200)
            check(page.locator(".wrow").count() >= 1 and "图书馆" in page.locator(".wrow").first.inner_text(), "%s: search pinyin without tones" % scheme)
            page.fill("#q", "")
            page.click('#filters button[data-f="new"]')
            page.wait_for_timeout(200)
            n_new = wcount(page)
            page.click('#filters button[data-f="learn"]')
            page.wait_for_timeout(200)
            n_learn = wcount(page)
            page.click('#filters button[data-f="all"]')
            check(n_new == 601 - len(pattern) and n_learn == len(pattern), "%s: filters À voir / En cours" % scheme, (n_new, n_learn))
            page.click('#wdeck button[data-deck="hsk1"]')
            page.wait_for_timeout(200)
            check(wcount(page) == 150 and page.locator(".wrow").count() == 150, "%s: list filter HSK 1" % scheme, wcount(page))
            page.click('#wdeck button[data-deck="all"]')
            page.click(".wrow >> nth=0")
            page.wait_for_timeout(600)
            shot(page, "%s-08-sheet" % scheme)
            meta = nb(page.inner_text("#sheet-body .meta"))
            check("Seau 1, prochaine révision demain" in meta, "%s: word sheet tells the bucket (还, √ first)" % scheme, meta)
            page.click("#sheet .close")
            page.click('.tab[data-view="progress"]')
            page.wait_for_timeout(300)
            pr = page.evaluate("""() => ({
              cols: document.querySelectorAll('#boxes .col').length,
              labels: [...document.querySelectorAll('#boxes-axis span')].map(s => s.firstChild.textContent),
              vals: [...document.querySelectorAll('#boxes-axis b')].map(b => +b.textContent),
              seen: document.querySelector('#seen-n').textContent,
              head: [...document.querySelectorAll('#decktable th')].map(t => t.textContent),
              fc: [...document.querySelectorAll('#forecast-axis b')].map(b => +b.textContent),
              evalOn: !document.querySelector('#eval-go').disabled, freeOn: !document.querySelector('#free-go').disabled,
            })""")
            check(pr["cols"] == 7 and [nb(x) for x in pr["labels"]] == ["ratés"] + DELAYS_OUT, "%s: seven buckets in Progress" % scheme, pr["labels"])
            check(pr["vals"] == [len(misses), len(ups), 0, 0, 0, 0, 0] and pr["seen"] == str(len(pattern)) and pr["fc"][:2] == [len(misses), len(ups)],
                  "%s: bucket counts, words passed, forecast" % scheme, pr)
            check(pr["head"] == ["Liste", "Passés", "À voir"] and pr["evalOn"] and pr["freeOn"], "%s: list table, evaluation and training buttons" % scheme, pr["head"])
            page.click("#forecast .col >> nth=1")
            shot(page, "%s-09-progress" % scheme, full=True)
            page.click('.tab[data-view="settings"]')
            page.wait_for_timeout(300)
            shot(page, "%s-10-settings" % scheme, full=True)
            ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            check(ov == 0, "%s: no horizontal overflow" % scheme, ov)
            sw = page.evaluate("() => [...document.querySelectorAll('#deck-settings .switch')].map(b => { const r = b.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })")
            check(sw and all(x == [48, 28] for x in sw), "%s: list switches drawn as switches" % scheme, sw)
            se = page.evaluate("""() => ({
              old: document.querySelectorAll('#new-plus, #new-minus, #new-val, [data-per], #more-new, .grade[data-g="2"]').length,
              steppers: document.querySelectorAll('#bucket-settings .stepper').length,
              outs: [...document.querySelectorAll('#bucket-settings output')].map(o => o.textContent),
              bk: [...document.querySelectorAll('#bucket-btns [data-bk]')].map(b => b.dataset.bk),
              order: document.querySelector('#new-order').textContent,
              ev: document.querySelector('#eval-val').textContent,
            })""")
            check(se["old"] == 0, "%s: no daily quota nor 优 button left" % scheme, se["old"])
            check(se["steppers"] == 6 and [nb(o) for o in se["outs"]] == DELAYS_OUT and se["bk"] == ["add", "remove"] and se["ev"] == "20",
                  "%s: buckets settings (6 delays, add / remove)" % scheme, se)
            check("HSK 3, puis HSK 2, puis HSK 1" in se["order"], "%s: first pass order explained" % scheme, se["order"])

            if scheme == "light":
                print("== new card from the header and from an empty search")
                page.click("#btn-new")
                page.wait_for_timeout(200)
                check(page.is_visible("#wform") and page.inner_text("#sheet-title") == "Ajouter un mot", "header button opens the form")
                page.click("#sheet .close")
                page.click('.tab[data-view="words"]')
                page.fill("#q", "pavillon")
                page.wait_for_timeout(200)
                page.click("#add-q")
                page.wait_for_timeout(200)
                check(page.input_value("#f-f") == "pavillon" and page.input_value("#f-h") == "", "empty search prefills the form")
                page.click("#sheet .close")
                page.fill("#q", "")
                print("== phone words, export, update from the computer")
                page.click('.tab[data-view="words"]')
                page.click("#btn-add")
                page.wait_for_timeout(200)
                page.fill("#f-h", "打印")
                page.fill("#f-p", "da3yin4")
                page.fill("#f-f", "imprimer")
                page.click(".more summary")
                page.fill("#f-e", "我要打印这张照片。")
                page.fill("#f-ef", "Je dois imprimer cette photo.")
                page.wait_for_timeout(150)
                shot(page, "light-11-add")
                page.click("#wform button[type=submit]")
                page.wait_for_timeout(300)
                tel = page.evaluate("() => state.custom.map(w => [w.id, w.h, w.p, w.e])")
                check(len(tel) == 1 and tel[0][1] == "打印", "word added on the phone", tel)
                first = page.evaluate("(id) => [study.queue[0], inPass(id)]", tel[0][0])
                check(first == [tel[0][0], True], "phone word next in the line (phone lists first)", first)
                tsv = page.evaluate("() => customTSV()")
                check(tsv == "打印\tdǎyìn\timprimer\t\t\t我要打印这张照片。\t\tJe dois imprimer cette photo.", "export line for perso.tsv", tsv)
                page.click("#btn-export")
                page.wait_for_timeout(250)
                shot(page, "light-12-export")
                page.click("#sheet .close")
                # learn it once on the phone
                page.evaluate("(id) => { applyGrade(id, true); save(); }", tel[0][0])
                # a word appears once in the dictionary: the same characters and pinyin are refused, and a word of a
                # list is offered to the list instead of being written again
                page.click("#btn-add")
                page.fill("#f-h", "打印")
                page.fill("#f-p", "da3yin4")
                page.fill("#f-f", "imprimer")
                page.click("#wform button[type=submit]")
                page.wait_for_timeout(150)
                check("déjà dans le dictionnaire (Ajoutés ici)" in nb(page.inner_text("#f-err")), "the same word refused", page.inner_text("#f-err"))
                page.fill("#f-h", "图书馆")
                page.wait_for_timeout(100)
                hint = page.inner_text("#f-hh")
                check("Déjà dans le dictionnaire" in hint and page.locator("#f-hh [data-take]").count() == 1, "a word of HSK 3 offered to the list", hint)
                page.click("#sheet .close")
                # the computer side: paste into perso.tsv, add a word, correct a word, publish
                with open(os.path.join(site, "decks", "perso.tsv"), "a", encoding="utf-8") as fh:
                    fh.write(tsv.replace("\t\tJe dois", "\tWǒ yào dǎyìn zhè zhāng zhàopiàn.\tJe dois") + "\n")
                    fh.write("复印\tfùyìn\tphotocopier\n")
                path3 = os.path.join(site, "decks", "hsk3.tsv")
                s3 = open(path3, encoding="utf-8").read()
                s3 = s3.replace("\trendre (qqch d’emprunté)\t", "\trendre (qqch d’emprunté) ; rembourser\t")
                open(path3, "w", encoding="utf-8").write(s3)
                page.click('.tab[data-view="settings"]')
                page.click("#lists-check")
                page.wait_for_function("() => !document.querySelector('#toast').hidden && document.querySelector('#toast').textContent.includes('mises à jour')", timeout=8000)
                msg = nb(page.inner_text("#toast"))
                print("  toast:", msg)
                shot(page, "light-13-update-toast")
                check("Perso" in msg and "2 mots ajoutés" in msg and "1 mot corrigé" in msg and "passé dans Perso" in msg, "update toast", msg)
                after = page.evaluate("""() => ({tel: state.custom.length, card: state.cards['perso:打印'], old: Object.keys(state.cards).filter(k => k.startsWith('u-')).length,
                    f: BYID.get('hsk3:还').f, perso: LISTBYID.get('perso').words.length,
                    stale: [study.cur, ...study.queue].filter(id => id && id.startsWith('u-')).length,
                    fresh: study.queue[0], learnt: [study.cur, ...study.queue].includes('perso:打印')})""")
                check(after["tel"] == 0 and after["card"] and after["card"]["r"] == 1 and after["card"]["b"] == 1 and after["old"] == 0 and after["perso"] == 2,
                      "phone word moved into Perso with its progress (bucket 1)", after)
                check(after["stale"] == 0 and after["fresh"] == "perso:复印" and not after["learnt"], "line rebuilt: no phone id left, new Perso word first", after)
                check("rembourser" in after["f"], "correction from the computer applied", after["f"])
                # switch a list off from the phone, then the computer switches another one off and adds a list
                page.click('.switch[data-deck="hsk1"]')
                off = page.evaluate("() => [deckOn('hsk1'), [study.cur, ...study.queue].some(id => id && id.startsWith('hsk1:'))]")
                check(off == [False, False], "list switched off on the phone", off)
                cfg = json.load(open(os.path.join(site, "decks", "decks.json"), encoding="utf-8"))
                for l in cfg["listes"]:
                    if l["id"] == "hsk2":
                        l["actif"] = False
                cfg["listes"].append({"id": "hsk30-3", "nom": "HSK 3.0 niveau 3", "fichier": "hsk30-3.tsv", "actif": True})
                json.dump(cfg, open(os.path.join(site, "decks", "decks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                with open(os.path.join(site, "decks", "hsk30-3.tsv"), "w", encoding="utf-8") as fh:
                    fh.write("hanzi\tpinyin\tfrancais\n安排\tānpái\torganiser\n")
                page.evaluate("() => refreshLists(false, true)")
                page.wait_for_function("() => document.querySelector('#toast').textContent.includes('nouvelle liste')", timeout=8000)
                msg2 = nb(page.inner_text("#toast"))
                print("  toast:", msg2)
                st = page.evaluate("""() => {
                  const L = [study.cur, ...study.queue].filter(Boolean), i = L.indexOf('hsk30-3:安排');
                  return { on2: deckOn('hsk2'), on1: deckOn('hsk1'), on30: deckOn('hsk30-3'), n30: LISTBYID.get('hsk30-3').words.length,
                    hsk2: L.filter(id => id.startsWith('hsk2:')).length, last: i >= 0 && L.slice(0, i).every(inPass) && L.slice(i + 1).every(missed) };
                }""")
                check(st == {"on2": False, "on1": False, "on30": True, "n30": 1, "hsk2": 0, "last": True},
                      "decks.json changes applied (HSK 2 off, new list after the others), phone switch kept", st)
                shot(page, "light-14-settings-after", full=True)
            ctx.close()
            httpd.shutdown()

        # ------------------------------------------------------------ migration from v1, offline, update banner
        print("== migration, offline, update banner")
        site = fresh_copy("site-mig")
        httpd, url = serve(site)
        ctx, page = new_page(browser, errors, offline_ok=True)
        page.add_init_script("""(() => {
          if (sessionStorage.getItem('seeded')) return;
          sessionStorage.setItem('seeded', '1');
          const d = new Date(Date.now() - 4 * 3600e3);
          const today = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 864e5);
          localStorage.setItem('xingyinyi.v1', JSON.stringify({ v: 1,
            settings: { newPerDay: 12, startFace: 2, autoAudio: false, rate: 0.8, toneColors: true },
            cards: { 'h3-109': { b: 3, d: today + 2, r: 4, l: 0, t: today - 2 }, 'h3-000': { b: 1, d: today, r: 1, l: 0, t: today - 1 }, 'u-abc': { b: 2, d: today + 1, r: 2, l: 0, t: today - 1 } },
            edits: { 'h3-001': { p: 'a', f: 'ah (corrigé)', n: '' } },
            custom: [{ id: 'u-abc', h: '打印', p: 'da3yin4', f: 'imprimer' }], log: {}, extra: null }));
        })();""")
        page.goto(url)
        wait_ready(page)
        mig = page.evaluate("""() => ({ per: 'newPerDay' in state.settings, face: state.settings.startFace, sched: state.sched,
            c109: state.cards['hsk3:' + LEGACY[109]], c0: state.cards['hsk3:' + LEGACY[0]], edit: state.edits['hsk3:' + LEGACY[1]],
            tel: state.custom.map(w => w.h), telCard: state.cards['u-abc'],
            pass: ['hsk3:' + LEGACY[109], 'hsk3:' + LEGACY[0], 'u-abc'].every(inPass), head: study.cur,
            v2: !!localStorage.getItem('xingyinyi.v2'), v1kept: !!localStorage.getItem('xingyinyi.v1'), toast: document.querySelector('#toast').textContent,
            due: [study.cur, ...study.queue].filter(id => id === 'hsk3:' + LEGACY[0]).length })""")
        print("  ", json.dumps(mig, ensure_ascii=False))
        check(not mig["per"] and mig["face"] == 2 and mig["sched"] == 1 and mig["edit"] and mig["tel"] == ["打印"]
              and mig["v2"] and mig["v1kept"] and "première version" in mig["toast"],
              "first version carried over (settings without daily quota, corrections, phone word)", mig)
        check(all(c and c["b"] == 0 and "d" not in c for c in (mig["c109"], mig["c0"], mig["telCard"]))
              and (mig["c109"]["r"], mig["c0"]["r"], mig["telCard"]["r"]) == (4, 1, 2) and mig["pass"] and mig["due"] == 1 and mig["head"] == "u-abc",
              "first version: every word back to bucket 0 for the first pass, reviews kept, phone word first", mig)
        check(page.evaluate("() => LEGACY[109]") == "极", "legacy index sanity")
        # offline start
        page.wait_for_function("() => navigator.serviceWorker && navigator.serviceWorker.controller", timeout=10000)
        page.wait_for_timeout(1500)
        ctx.set_offline(True)
        page.reload()
        wait_ready(page)
        off = page.evaluate("() => ({ ready: listsReady, n: DECK.length, font: document.fonts.check('20px WK', '图书馆'), cur: !!study.cur })")
        check(off["ready"] and off["n"] == 602 and off["cur"], "offline start with lists (601 + 1 phone word)", off)
        shot(page, "light-15-offline")
        ctx.set_offline(False)
        # app update: a new sw.js on the server shows the banner
        with open(os.path.join(site, "sw.js"), "a", encoding="utf-8") as fh:
            fh.write("\n// v2\n")
        page.evaluate("() => swReg && swReg.update()")
        page.wait_for_selector("#updatebar:not([hidden])", timeout=10000)
        shot(page, "light-16-update-banner")
        check(True, "update banner after a new service worker")
        ctx.close()
        httpd.shutdown()

        # ------------------------------------------------------------ boxes and daily quotas (v2 without sched) -> buckets
        print("== boxes -> buckets")
        site = fresh_copy("site-mig2")
        httpd, url = serve(site)
        ctx, page = new_page(browser, errors)
        page.add_init_script(SEED_BOXES)
        page.goto(url)
        wait_ready(page)
        shot(page, "light-17-buckets-toast")
        m = page.evaluate("""() => ({ cards: state.cards, sched: state.sched, per: 'newPerDay' in state.settings, face: state.settings.startFace,
            delays: state.settings.delays, decks: state.decks, toast: document.querySelector('#toast').textContent, flag: migratedSched,
            pass: Object.keys(state.cards).every(inPass), cur: study.cur, n: [study.cur, ...study.queue].length,
            saved: JSON.parse(localStorage.getItem('xingyinyi.v2')).sched, before: !!localStorage.getItem('xingyinyi.avant-seaux') })""")
        cs = m["cards"]
        print("  ", json.dumps(cs, ensure_ascii=False))
        check(m["sched"] == 1 and m["saved"] == 1 and m["flag"] and "Nouveau planning en seaux" in nb(m["toast"]), "old planning detected, toast shown", (m["sched"], m["toast"]))
        check(sorted(cs) == sorted(OLD_IDS) and all(c["b"] == 0 and "d" not in c and "k" not in c for c in cs.values()) and m["pass"],
              "every card back to bucket 0, first pass again", cs)
        check([(cs[i]["r"], cs[i]["l"]) for i in OLD_IDS if i in cs] == [(6, 1), (1, 0), (3, 0), (2, 1)], "reviews and lapses kept", cs)
        check(not m["per"] and m["face"] == 1 and m["delays"] == [1, 3, 7, 14, 30, 60]
              and not any("perDay" in d or "cfgPer" in d for d in m["decks"].values()), "daily quotas dropped, other settings kept", (m["face"], m["decks"]))
        check(m["cur"] == "hsk3:还" and m["n"] == 601 and m["before"], "line starts again from the top, old progress kept aside", (m["cur"], m["n"], m["before"]))
        g = answer(page, 1)
        page.reload()
        wait_ready(page)
        r = page.evaluate("(id) => ({ c: state.cards[id], flag: migratedSched, toast: document.querySelector('#toast').textContent, inLine: [study.cur, ...study.queue].includes(id) })", g)
        check(g == "hsk3:还" and r["c"] and r["c"]["b"] == 1 and r["c"]["r"] == 7 and not r["flag"] and "Nouveau planning" not in nb(r["toast"]) and not r["inLine"],
              "no second migration after a reload (the word answered keeps bucket 1)", r)
        ctx.close()
        httpd.shutdown()

        # ------------------------------------------------------------ small phone and first launch without network
        print("== small phone, first launch offline")
        site = fresh_copy("site-small")
        httpd, url = serve(site)
        ctx, page = new_page(browser, errors, "light", size=(375, 667))
        page.goto(url)
        wait_ready(page)
        page.click("#turnbtn")
        page.wait_for_timeout(700)
        shot(page, "small-01-turned")
        box = page.evaluate("() => { const g = document.querySelector('#grades').getBoundingClientRect(); const m = document.querySelector('#main').getBoundingClientRect(); return [g.bottom, m.bottom]; }")
        check(box[0] <= box[1] + 1, "small phone: grades visible after turning", box)
        ctx.close()
        ctx, page = new_page(browser, errors, "light", offline_ok=True)
        page.route("**/decks/**", lambda route: route.abort())
        page.goto(url)
        page.wait_for_selector("#loading-retry:not([hidden])", timeout=10000)
        shot(page, "small-02-load-error")
        check("decks/" in page.inner_text("#loading-text"), "clear message when lists cannot load", page.inner_text("#loading-text"))
        ctx.close()

        # ------------------------------------------------------------ a computer screen (the installed app, 900 px and more)
        print("== ordinateur")
        ctx, page = new_page(browser, errors, size=(1366, 768), mobile=False)
        page.goto(url)
        wait_ready(page)

        def shots(name):        # each screen in light, then in dark: the same layout (console errors in dark are caught too)
            shot(page, name + "-light")
            light = page.evaluate(LAYOUT)
            page.emulate_media(color_scheme="dark")
            shot(page, name + "-dark")
            dark = page.evaluate(LAYOUT)
            check(dark == light, name + ": the same layout in dark", {"light": light, "dark": dark})
            page.emulate_media(color_scheme="light")

        def open_word(n):       # Mots: the sheet of the list's n-th word
            page.click("#wlist .wrow >> nth=%d" % n)
            page.wait_for_selector("#sheet:not([hidden]) #sheet-stage")

        # the card's sizes found by halving (shrink) are those of the old loop, size after size
        same = page.evaluate("""() => { const loop = (start, floor, step, cut) => { let s = start; while (s > cut && s > floor) s -= step; return s; };
            for (const [start, floor, step] of [[19, 13, 1], [49, 13, 1], [16, 15, 1], [46, 18, 2], [79, 18, 2], [12, 13, 1]])
              for (let cut = 0; cut <= start + 1; cut++) {
                let v = 0; const got = shrink(start, floor, step, x => { v = x; }, () => v > cut);
                if (got !== loop(start, floor, step, cut) || v !== got) return [start, floor, step, cut, got, v];
              }
            return true; }""")
        check(same is True, "the sizes on the card: the halving finds what the loop did", same)
        lay = page.evaluate("() => { " + RECT + """ const tabs = [...document.querySelectorAll('.tab')].map(t => t.getBoundingClientRect());
            return { nav: r('.tabs').right, brand: r('.brand').left, mainL: r('#main').left, column: tabs.every((t, i) => !i || t.top > tabs[i - 1].top),
              stage: r('#stage'), example: r('#example'), turn: r('#turnbtn'), card: [prism.w, prism.h], main: r('#main').height,
              keys: getComputedStyle(document.querySelector('.keys')).display }; }""")
        check(lay["column"] and lay["nav"] <= lay["mainL"] + 1 and lay["brand"] < 30, "the sections in a menu on the left, the name above them", lay)
        check(lay["example"]["left"] > lay["stage"]["left"] + lay["card"][0] and lay["turn"]["left"] > lay["stage"]["left"] + lay["card"][0]
              and lay["card"][0] >= 500 and lay["card"][1] <= lay["main"], "a large card, the example and the answers beside it", lay)
        check(lay["keys"] == "block", "the keyboard keys under the answers", lay["keys"])
        page.click("#turnbtn")
        page.wait_for_timeout(700)
        shots("pc-01-revision")
        answer(page, 1, key=True)
        page.click(".tab[data-view='words']")
        open_word(1)
        first = page.evaluate(SHEET)["open"]
        dock = page.evaluate("""() => { const s = document.querySelector('#sheet'), left = s.getBoundingClientRect().left;
            return { dock: s.classList.contains('dock'), veil: getComputedStyle(s.querySelector('.veil')).display, modal: s.querySelector('.panel').getAttribute('aria-modal'),
                     row: document.querySelector('#wlist .wrow').getBoundingClientRect().right <= left + 1,
                     scroll: document.querySelector('main').getBoundingClientRect().right <= left + 1 }; }""")
        check(dock["dock"] and dock["veil"] == "none" and dock["modal"] == "false" and dock["row"] and dock["scroll"],
              "Mots: the word's sheet beside the list, not modal (the list stays usable, its scroll bar left of the sheet)", dock)
        page.click("#wlist .wrow >> nth=2")
        page.wait_for_function("(t) => sheetWord && sheetWord !== t", arg=first)
        mark = page.evaluate(SHEET)
        check(mark["marked"] == [mark["open"]] and mark["focus"] == "row",
              "another word of the list: its sheet in the same place, its row marked instead, the focus still on it", mark)
        shots("pc-02-mots")
        # a click that leaves no focus on the row (Safari): the focus goes to the word's row, not into the sheet
        page.evaluate("() => { document.activeElement.blur(); wordSheet(document.querySelectorAll('#wlist .wrow')[3].dataset.id); }")
        page.wait_for_timeout(120)
        mark = page.evaluate(SHEET)
        check(mark["marked"] == [mark["open"]] and mark["focus"] == "row", "a sheet beside the list opened without focus: the focus on its row", mark)
        page.set_viewport_size({"width": 1000, "height": 768})
        page.wait_for_function("() => !document.querySelector('#sheet').classList.contains('dock')")
        mark = page.evaluate(SHEET)
        check(mark["shown"] and mark["modal"] == "true" and mark["marked"] == [] and mark["open"] is None and mark["focus"] == "sheet",
              "the window made narrower: the sheet over a veil, its row no longer marked, the focus in the sheet", mark)
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 1366, "height": 768})
        page.click("#btn-add")
        page.wait_for_selector("#sheet:not([hidden]) #f-p")
        form = page.evaluate("() => ({ dock: document.querySelector('#sheet').classList.contains('dock'), veil: getComputedStyle(document.querySelector('#sheet .veil')).display })")
        check(not form["dock"] and form["veil"] != "none", "a form keeps its veil (a click on the list cannot lose it)", form)
        page.keyboard.press("Escape")
        open_word(1)
        page.click(".tab[data-view='progress']")
        prog = page.evaluate("""() => ({ sheet: document.querySelector('#sheet').hidden,
            lefts: [...new Set([...document.querySelectorAll('#view-progress .section')].map(x => Math.round(x.getBoundingClientRect().left)))].length })""")
        check(prog["sheet"] and prog["lefts"] >= 2, "another section closes the word's sheet; Progrès in columns", prog)
        shots("pc-03-progres")
        page.click(".tab[data-view='settings']")
        check(page.evaluate("() => new Set([...document.querySelectorAll('#view-settings .sgroup')].map(x => Math.round(x.getBoundingClientRect().left))).size") >= 2,
              "Réglages in columns")
        shots("pc-04-reglages")
        page.click(".tab[data-view='study']")
        page.evaluate("() => showSteps(prism.root, BYID.get(study.cur))")
        page.wait_for_selector("#sheet:not([hidden]) #sheet-traits")
        side = page.evaluate("() => { const s = document.querySelector('#sheet'); return { dock: s.classList.contains('dock'), panel: s.querySelector('.panel').getBoundingClientRect().left, w: innerWidth }; }")
        check(not side["dock"] and side["panel"] > side["w"] / 3, "elsewhere, a sheet opens on the right, over a veil", side)
        page.keyboard.press("Escape")
        page.click("#startface button[aria-checked='true']")
        page.keyboard.press(" ")
        check(page.evaluate("() => prism.turns !== prism.start"), "Space after a mouse click on « D’abord »: the card turns")
        page.focus(".tab[data-view='words']")
        page.keyboard.press("Enter")
        check(page.evaluate("() => current") == "words", "Enter on another entry of the menu opens it (does not turn the card)")
        page.click(".tab[data-view='study']")
        for w, h in ((1000, 700), (900, 700), (1536, 700), (2560, 1440)):
            page.set_viewport_size({"width": w, "height": h})
            page.wait_for_timeout(250)
            page.evaluate("() => { redrawCurrent(); prism.layout(); }")
            page.click("#turnbtn")
            page.wait_for_timeout(650)
            fitv = page.evaluate("""() => { const m = document.querySelector('#main'), st = document.querySelector('#stage').getBoundingClientRect(),
                a = document.querySelector('#actions').getBoundingClientRect(), mr = m.getBoundingClientRect();
                return { sx: m.scrollWidth - m.clientWidth, sy: m.scrollHeight - m.clientHeight, left: st.left >= mr.left, right: a.right <= mr.right + 1, card: [prism.w, prism.h] }; }""")
            check(fitv["sx"] <= 0 and fitv["sy"] <= 0 and fitv["left"] and fitv["right"], "%d×%d: the card and the answers fit the window, no scroll bar" % (w, h), fitv)
            if (w, h) == (2560, 1440):
                check(fitv["card"][0] >= 900, "a large screen, a large card", fitv["card"])
                shots("pc-05-grand-ecran")
            answer(page, 1, key=True)
        turns = page.evaluate("() => { showDone(); document.activeElement.blur(); return prism.turns; }")
        page.keyboard.press(" ")
        after = page.evaluate("() => ({ turns: prism.turns, grades: document.querySelector('#grades').hidden })")
        check(after["turns"] == turns and after["grades"], "the end screen: Space turns no hidden card", after)
        page.set_viewport_size({"width": 1000, "height": 700})
        page.click(".tab[data-view='words']")
        open_word(1)
        check(page.evaluate("() => !document.querySelector('#sheet').classList.contains('dock')"), "1000 px: no room beside the list, the word's sheet over a veil")
        page.keyboard.press("Escape")
        page.set_viewport_size({"width": 932, "height": 430})
        land = page.evaluate(BARS)
        check(land["tabs"] >= land["main"] - 1, "a large phone held sideways keeps the phone's layout", land)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        phone = page.evaluate(BARS)
        check(phone["tabs"] >= phone["main"] - 1 and phone["card"] <= 380, "the window made narrow: the phone's layout again", phone)
        ctx.close()
        httpd.shutdown()

        browser.close()

    finish(errors)


if __name__ == "__main__":
    main()
