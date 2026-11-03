# -*- coding: utf-8 -*-
"""Onglet HSK : les parties du HSK 3 (2.0) sans les images, en exercice (corrigé à chaque question) et en examen blanc.

    py tests\\test_hsk.py

La voix est remplacée par une voix factice qui note ce qu'elle dit (deux voix : Tingting, une femme, et Li-Mu, un homme) ;
les attentes de l'examen blanc sont raccourcies (hsk.pace).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commun import check, fresh_copy, serve, new_page, wait_ready, shot, finish, nb, REPO  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

VOICE = """
window.__said = [];
(() => {
  const voices = [{ name: "Tingting", lang: "zh-CN" }, { name: "Li-Mu", lang: "zh-CN" }];
  const stub = { getVoices: () => voices, cancel() {}, addEventListener() {},
    speak(u) { __said.push({ text: u.text, voice: u.voice && u.voice.name, pitch: u.pitch }); setTimeout(() => u.onend && u.onend(), 15); } };
  Object.defineProperty(window, "speechSynthesis", { value: stub, configurable: true });
  window.SpeechSynthesisUtterance = function (t) { this.text = t; };
})();
"""
CUR = """() => { const r = state.hskRun, p = r.pages[r.i], it = hskItem(p);
  return { k: p.k, id: p.id, perm: p.perm || null, cands: p.cands || null, it, i: r.i, sec: r.sec, chk: r.chk.includes(r.i) }; }"""
DATA = json.load(open(os.path.join(REPO, "exos", "hsk3.json"), encoding="utf-8"))


def no_overflow(page, label):
    w = page.evaluate("() => [document.querySelector('#main').scrollWidth, document.querySelector('#main').clientWidth]")
    check(w[0] <= w[1], "no sideways scroll: " + label, w)


def open_hsk(page):
    page.click('.tab[data-view="hsk"]')
    page.wait_for_selector("#hsk-home .hsk-part, #hsk-run:not([hidden])")


def start_part(page, k):
    open_hsk(page)
    page.click('.hsk-part[data-part="%s"]' % k)
    page.wait_for_selector("#hsk-run:not([hidden]) #hsk-page .hsk-n")


def right_single(page, c):
    """Clicks the right answer of a page with one question; returns its selector."""
    it = c["it"]
    sel = {"e2": '.hsk-opt[data-a="%s"]' % ("true" if it.get("ok") else "false"),
           "w2": '.hsk-kb [data-a="%s"]' % it.get("ch")}.get(c["k"], '.hsk-opt[data-a="%s"]' % it.get("ans"))
    page.click("#hsk-page " + sel)
    return sel


def wrong_single(page, c):
    it = c["it"]
    if c["k"] == "e2":
        page.click('#hsk-page .hsk-opt[data-a="%s"]' % ("false" if it["ok"] else "true"))
    else:
        page.click('#hsk-page .hsk-opt[data-a="%d"]' % ((it["ans"] + 1) % 3))


def main():
    site = fresh_copy("site-hsk")
    httpd, url = serve(site)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = new_page(browser, errors)
        ctx.add_init_script(VOICE)
        page.goto(url)
        wait_ready(page)

        print("data")
        counts = {k: len(DATA[k]) for k in ("e2", "e3", "e4", "l1", "l2", "l3", "w1")}
        check(all(counts[k] >= 10 for k in ("e2", "e3", "e4", "l3")) and counts["l1"] >= 2 and counts["l2"] >= 2 and counts["w1"] >= 5,
              "exos/hsk3.json holds a mock exam at least", counts)
        fiches = DATA["fiches"]
        per = {f["id"]: sum(1 for x in DATA["w1"] if x.get("g") == f["id"]) for f in fiches}
        check(len(fiches) >= 15 and min(per.values()) >= 5, "fiches of word order, five sentences each at least", per)

        print("home")
        open_hsk(page)
        check(page.locator(".hsk-part[data-part]").count() == 8, "eight parts (the listening without its pictures)", page.locator(".hsk-part[data-part]").count())
        check(page.locator(".hsk-part[data-fiche]").count() == len(fiches), "a row per fiche of word order", page.locator(".hsk-part[data-fiche]").count())
        rows = nb(page.inner_text("#hsk-home .hsk-parts"))
        check("0 sur 30 faites" in rows and "Caractère d’après son pinyin" in rows, "each part with its questions done", rows[:200])
        check("Examen le" in nb(page.inner_text("#hsk-home")), "the exam's date and the days left", page.inner_text("#hsk-home")[:300])
        no_overflow(page, "home")
        shot(page, "hsk-accueil")

        print("practice: true or false")
        start_part(page, "e2")
        c = page.evaluate(CUR)
        page.wait_for_function("() => __said.length > 0")
        said = page.evaluate("() => __said")
        check(said[0]["text"] == c["it"]["t"]["zh"], "the sentence is heard (once in a practice)", said[:2])
        check(c["it"]["q"]["zh"] in page.inner_text("#hsk-page") and c["it"]["t"]["zh"] not in page.inner_text("#hsk-page"),
              "the statement shown, the sentence heard only")
        right_single(page, c)
        page.wait_for_selector("#hsk-page .hsk-corr")
        corr = page.inner_text("#hsk-page .hsk-corr")
        check("Juste" in corr and c["it"]["t"]["zh"] in corr and c["it"]["t"]["fr"].split(" ")[0] in corr,
              "corrected at once: what was heard, its pinyin and translation", corr[:200])
        check(page.locator("#hsk-page .hsk-py span.t1, #hsk-page .hsk-py span.t2, #hsk-page .hsk-py span.t3, #hsk-page .hsk-py span.t4").count() > 0, "the pinyin in tones")
        ok_n = 1
        for n in range(9):
            page.click('#hsk-page [data-hsk="next"]')
            page.wait_for_function("(i) => state.hskRun.i === i", arg=n + 1)
            c = page.evaluate(CUR)
            if n % 2:
                right_single(page, c)
                ok_n += 1
            else:
                wrong_single(page, c)
            page.wait_for_selector("#hsk-page .hsk-corr")
        check("Raté" in page.inner_text("#hsk-page .hsk-corr") or "Juste" in page.inner_text("#hsk-page .hsk-corr"), "each answer corrected")
        check(nb(page.inner_text('#hsk-page [data-hsk="next"]')) == "Voir le résultat", "the last question leads to the result")
        page.click('#hsk-page [data-hsk="next"]')
        page.wait_for_selector("#hsk-page .hsk-score")
        check(page.inner_text("#hsk-page .hsk-score b") == str(ok_n), "the score of the practice", page.inner_text("#hsk-page .hsk-score"))
        log = page.evaluate("() => state.hskLog[0]")
        check(log["k"] == "e2" and len(log["ok"]) == ok_n and len(log["ko"]) == 10 - ok_n, "the result kept (questions passed and missed)", log)
        check(page.locator("#hsk-page details.hsk-miss").count() == 10 - ok_n, "the questions missed, with their correction",
              page.locator("#hsk-page details.hsk-miss").count())
        page.click('#hsk-page [data-hsk="home"]')
        page.wait_for_selector("#hsk-home .hsk-part")
        row = nb(page.inner_text('.hsk-part[data-part="e2"]'))
        check(("%d/10" % ok_n) in row and "10 sur 30 faites" in row, "the part shows its last score", row)
        page.click('.hsk-part[data-part="e2"]')
        page.wait_for_selector("#hsk-page .hsk-n")
        firsts = page.evaluate("() => state.hskRun.pages.map(p => p.id)")
        check(not set(firsts) & set(log["ok"] + log["ko"]), "the questions never asked come first", firsts)
        page.click("#hsk-stop")                       # stopped before any answer: nothing kept
        page.wait_for_selector("#hsk-home .hsk-part")
        check(page.evaluate("() => state.hskRun === null && state.hskLog.length === 1"), "a practice stopped before its first answer leaves nothing")

        print("practice: a dialogue, its voices")
        page.evaluate("() => { __said.length = 0; }")
        start_part(page, "e3")
        c = page.evaluate(CUR)
        n_lines = len(c["it"]["dia"]) + 1
        page.wait_for_function("(n) => __said.length >= n", arg=n_lines)
        said = page.evaluate("() => __said")
        dia = c["it"]["dia"]
        check([s["text"] for s in said[:n_lines]] == [d["zh"] for d in dia] + ["问：" + c["it"]["q"]["zh"]], "the dialogue, then its question", said)
        check(all(s["voice"] == ("Li-Mu" if d["s"] == "男" else "Tingting") for s, d in zip(said, dia)), "a man's voice and a woman's", said)
        opts = page.locator("#hsk-page .hsk-opt").all_inner_texts()
        check([o.split("\n")[0].strip() for o in opts] == ["A", "B", "C"] and sorted(o.split("\n")[-1].strip() for o in opts) == sorted(x["zh"] for x in c["it"]["opts"]),
              "three answers lettered A, B, C, in another order", opts)
        wrong_single(page, c)
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.locator('#hsk-page .hsk-opt.ok[data-a="%d"]' % c["it"]["ans"]).count() == 1 and page.locator("#hsk-page .hsk-opt.ko").count() == 1,
              "the right answer marked, and the one given")
        corr = page.inner_text("#hsk-page .hsk-corr")
        check("Raté" in corr and dia[0]["s"] + "：" + dia[0]["zh"] in corr and "问：" in corr, "the dialogue in the correction", corr[:300])
        page.evaluate("() => { __said.length = 0; }")
        page.click('#hsk-page [data-hsk="replay"]')
        page.wait_for_function("(n) => __said.length >= n", arg=n_lines)
        check(page.evaluate("() => __said[0].text") == dia[0]["zh"], "Écouter: the dialogue again")
        no_overflow(page, "dialogue")
        shot(page, "hsk-dialogue-corrige")
        page.click("#hsk-stop")                       # stopped after one answer: its result is kept
        page.wait_for_selector("#hsk-page .hsk-score")
        check(page.evaluate("() => state.hskLog[0].k === 'e3' && state.hskLog[0].ko.length === 1 && !state.hskLog[0].ok.length"), "Arrêter: the questions answered count")
        page.click('#hsk-page [data-hsk="home"]')

        print("practice: reading, part 1")
        start_part(page, "l1")
        c = page.evaluate(CUR)
        check(page.locator("#hsk-page .hsk-gq").count() == 5 and page.locator("#hsk-page .hsk-bank li").count() == 5, "five sentences, five answers")
        perm = c["perm"]
        # the letter of pair 1 on sentence 0 then on sentence 1: it leaves sentence 0
        page.click('#hsk-page .hsk-letters [data-q="0"][data-a="1"]')
        page.click('#hsk-page .hsk-letters [data-q="1"][data-a="1"]')
        a = page.evaluate("() => state.hskRun.ans")
        check(a.get(c["id"] + ".1") == 1 and (c["id"] + ".0") not in a, "a letter goes to one sentence only", a)
        check(page.locator("#hsk-page .hsk-bank li.used").count() == 1, "the letter used is dimmed")
        for j in (0, 2, 3):                           # sentences 0 to 3 right (1 already is), the last one left without an answer
            page.click('#hsk-page .hsk-letters [data-q="%d"][data-a="%d"]' % (j, j))
        page.click('#hsk-page [data-hsk="check"]')
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(nb(page.inner_text("#hsk-page .hsk-verdict")).startswith("4 sur 5"), "corrected together: 4 sur 5", page.inner_text("#hsk-page .hsk-verdict"))
        check(page.locator("#hsk-page .hsk-letters button.ok").count() == 5, "the right letter of each sentence shown")
        no_overflow(page, "reading 1")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-page .hsk-score")
        page.click('#hsk-page [data-hsk="home"]')

        print("practice: reading, part 2")
        start_part(page, "l2")
        c = page.evaluate(CUR)
        it = c["it"]
        check(page.locator("#hsk-page .hsk-bank.words > span").count() == 6, "six words lettered A to F")
        for j, x in enumerate(it["items"]):
            page.click('#hsk-page .hsk-letters [data-q="%d"][data-a="%s"]' % (j, x["mot"]))
        blank = page.inner_text("#hsk-page .hsk-gq .hsk-blank")
        check(blank == it["items"][0]["mot"], "the word chosen fills the blank", blank)
        dialogue = any("\n" in x["zh"] for x in it["items"])
        check(not dialogue or page.locator("#hsk-page .hsk-gq br").count() > 0, "a dialogue on two lines")
        page.click('#hsk-page [data-hsk="check"]')
        page.wait_for_selector("#hsk-page .hsk-corr")
        corr = page.inner_text("#hsk-page .hsk-corr")
        check(nb(page.inner_text("#hsk-page .hsk-verdict")).startswith("5 sur 5") and "Les mots" in corr, "all right; the six words with their meaning", corr[-300:])
        check(page.locator("#hsk-page .hsk-corr mark").count() >= 5, "the word marked in each sentence")
        no_overflow(page, "reading 2")
        shot(page, "hsk-mot-a-placer")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-page .hsk-score")
        page.click('#hsk-page [data-hsk="home"]')

        print("practice: words in order")
        alt = next(x for x in DATA["w1"] if x.get("alt"))
        page.evaluate("""(id) => { const it = HSK_BY.get(id), perm = [...it.blocs.keys()].reverse();
            state.hskRun = { kind: 'part', k: 'w1', start: Date.now(), at: 0, pages: [{ k: 'w1', id, perm }], ans: {}, i: 0, chk: [], sec: 2, ends: 0, left: 0, pause: false, done: false };
            renderHsk(true); }""", alt["id"])
        target = alt["alt"][0].rstrip("。？！")
        order, rest = [], target
        while rest:                                   # the blocks of the other right order
            b = next(i for i, x in enumerate(alt["blocs"]) if rest.startswith(x) and i not in order)
            order.append(b)
            rest = rest[len(alt["blocs"][b]):]
        page.click('#hsk-page .bloc[data-in="%d"]' % order[0])
        page.click('#hsk-page .bloc[data-in="%d"]' % order[1])
        page.click('#hsk-page .hsk-line .bloc[data-out="1"]')   # taken back out
        check(page.evaluate("() => state.hskRun.ans[state.hskRun.pages[0].id]") == order[:1], "a block taken back out of the sentence")
        for b in order[1:]:
            page.click('#hsk-page .bloc[data-in="%d"]' % b)
        check(page.inner_text("#hsk-page .hsk-line").replace("\n", "") == target, "the blocks make the sentence", page.inner_text("#hsk-page .hsk-line"))
        page.click('#hsk-page [data-hsk="check"]')
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.inner_text("#hsk-page .hsk-verdict") == "Juste" and "Juste aussi" in page.inner_text("#hsk-page .hsk-corr"),
              "another right order is right too", page.inner_text("#hsk-page .hsk-corr")[:200])
        shot(page, "hsk-ordre")
        page.click('#hsk-page [data-hsk="next"]')
        page.wait_for_selector("#hsk-page .hsk-score")
        page.click('#hsk-page [data-hsk="home"]')

        print("word order: a fiche, then its sentences")
        f = next(x for x in fiches if x["id"] == "ba")
        mine = {x["id"] for x in DATA["w1"] if x.get("g") == "ba"}
        page.click('.hsk-part[data-fiche="ba"]')
        page.wait_for_selector("#sheet:not([hidden]) .fiche")
        body = nb(page.inner_text("#sheet-body"))
        check(nb(page.inner_text("#sheet-title")) == f["nom"], "the fiche's name on top", page.inner_text("#sheet-title"))
        check(page.locator("#sheet-body .slot").count() == sum(len(s["slots"]) for s in f["schemas"]) and page.locator("#sheet-body .slot.on").count() >= 1,
              "its pattern in boxes, the rule's marked", page.locator("#sheet-body .slot").count())
        check(page.locator("#sheet-body .fiche-ex").count() == len(f["ex"]) and f["ex"][0]["py"].split(" ")[0] in body and f["ex"][0]["fr"].split(" ")[0] in body,
              "its examples with their pinyin and translation", body[:200])
        check(page.locator("#sheet-body .fiche-trap").count() == len(f["pieges"]) and page.locator("#sheet-body .fiche-trap s").first.inner_text() == f["pieges"][0]["ko"],
              "its mistakes, struck out, then right")
        check(page.locator("#sheet-body .fiche-p .zh").count() > 0, "the Chinese of its text in the Chinese font")
        page.evaluate("() => { __said.length = 0; }")
        page.click("#sheet-body .fiche-ex [data-fsay]")
        check(page.evaluate("() => __said.map(s => s.text)") == [f["ex"][0]["zh"]], "an example heard", page.evaluate("() => __said"))
        no_overflow(page, "fiche")
        shot(page, "hsk-fiche")
        page.click('#sheet-body [data-fgo="ba"]')
        page.wait_for_selector("#hsk-run:not([hidden]) #hsk-page .hsk-pool")
        run = page.evaluate("() => ({ g: state.hskRun.g, ids: state.hskRun.pages.map(p => p.id), k: state.hskRun.k })")
        check(run["g"] == "ba" and run["k"] == "w1" and set(run["ids"]) <= mine and len(run["ids"]) == min(10, len(mine)),
              "S’entraîner: ten sentences of this fiche only", run)
        check(f["tag"] in page.inner_text("#hsk-where"), "the fiche on top of the practice", page.inner_text("#hsk-where"))
        page.click('#hsk-page [data-fiche="ba"]')        # the fiche again, from the exercise
        page.wait_for_selector("#sheet:not([hidden]) .fiche")
        check(page.locator('#sheet-body [data-fgo=""]').inner_text() == "Retour à l’exercice", "from the exercise: back to it")
        page.click('#sheet-body [data-fgo=""]')
        check(page.is_hidden("#sheet") and page.evaluate("() => state.hskRun.i") == 0, "the exercise where it was")
        c = page.evaluate(CUR)
        order, rest = [], c["it"]["zh"].rstrip("。？！")
        while rest:
            b = next(i for i, x in enumerate(c["it"]["blocs"]) if rest.startswith(x) and i not in order)
            order.append(b)
            rest = rest[len(c["it"]["blocs"][b]):]
        for b in order:
            page.click('#hsk-page .bloc[data-in="%d"]' % b)
        page.click('#hsk-page [data-hsk="check"]')
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.inner_text("#hsk-page .hsk-verdict") == "Juste" and page.locator('#hsk-page .hsk-rule [data-fiche="ba"]').count() == 1,
              "corrected, with the rule to see again")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-page .hsk-score")
        e = page.evaluate("() => state.hskLog[0]")
        check(e["k"] == "w1" and e.get("g") == "ba" and e["ok"] == [c["id"]] and not e["ko"], "the result kept with its fiche", e)
        check(page.locator('#hsk-page [data-hsk="again"]').inner_text() == "Recommencer" and page.locator('#hsk-page [data-fiche="ba"]').count() == 1,
              "at the end: Recommencer, La fiche")
        page.click('#hsk-page [data-hsk="again"]')
        page.wait_for_selector("#hsk-page .hsk-pool")
        again = page.evaluate("() => ({ g: state.hskRun.g, first: state.hskRun.pages.map(p => p.id) })")
        check(again["g"] == "ba" and c["id"] not in again["first"], "Recommencer: the same fiche, the sentence done last", again)
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-home .hsk-part")
        row = nb(page.inner_text('.hsk-part[data-fiche="ba"]'))
        check("1/1" in row and ("1 sur %d faites" % len(mine)) in row, "the fiche shows its last score", row)
        check(f["tag"] in page.inner_text("#hsk-home .hsk-log"), "the last results name the fiche", page.inner_text("#hsk-home .hsk-log")[:200])
        w1row = nb(page.inner_text('.hsk-part[data-part="w1"]'))
        own = page.evaluate("() => { const e = state.hskLog.find(e => e.k === 'w1' && !e.g); return e.ok.length + '/' + (e.ok.length + e.ko.length); }")
        check(own in w1row and "2 sur %d faites" % len(DATA["w1"]) in w1row, "writing 1: its own last score, every sentence done", w1row)
        page.click('#hsk-home [data-part="w1"].btn')    # every rule mixed
        page.wait_for_selector("#hsk-page .hsk-pool")
        check(page.evaluate("() => state.hskRun.g === undefined && state.hskRun.k === 'w1'"), "Toutes les règles mélangées: writing 1")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-home .hsk-part")

        print("practice: a character from its pinyin, on the keyboard")
        page.click('[data-hskw="clavier"]')
        check(page.evaluate("() => state.settings.hskWrite") == "clavier", "Au clavier chosen")
        page.click('.hsk-part[data-part="w2"]')
        page.wait_for_selector("#hsk-page .hsk-kb")
        c = page.evaluate(CUR)
        it = c["it"]
        hole = page.inner_text("#hsk-page .hsk-hole .py")
        check(it["ch"] in c["cands"] and len(c["cands"]) >= 2 and it["zh"][it["at"]] == it["ch"] and it["ch"] in it["w"]["h"],
              "the character of the word hidden, among others", c["cands"])
        check(hole == it["py"] and page.inner_text("#hsk-page .hsk-hole .ch") == "", "its syllable above the empty hole", hole)
        right_single(page, c)
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.inner_text("#hsk-page .hsk-verdict") == "Juste" and it["w"]["h"] in page.inner_text("#hsk-page .hsk-corr"), "right; the word in the correction")
        page.click('#hsk-page [data-hsk="next"]')
        page.click('#hsk-page [data-hsk="idk"]')
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.inner_text("#hsk-page .hsk-verdict") == "Pas de réponse", "Je ne sais pas: no answer")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-page .hsk-score")
        page.click('#hsk-page [data-hsk="home"]')

        print("practice: a character from its pinyin, by hand")
        page.click('[data-hskw="main"]')
        page.click('.hsk-part[data-part="w2"]')
        page.wait_for_selector("#hsk-pad")
        c = page.evaluate(CUR)
        ch = c["it"]["ch"]
        meds = page.evaluate("async (ch) => (await strokesOf(ch))[1]", ch)
        box = page.locator("#hsk-pad").bounding_box()
        cdp = ctx.new_cdp_session(page)
        for st in meds:
            pts = [(box["x"] + (x / 1024) * box["width"], box["y"] + ((900 - y) / 1024) * box["height"]) for x, y in st]
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": pts[0][0], "y": pts[0][1]}]})
            for x, y in pts[1:]:
                cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_function("(n) => hsk.pad.strokes.length === n && document.querySelectorAll('#hsk-cands [data-a]').length > 0", arg=len(meds), timeout=20000)
        cands = page.evaluate("() => [...document.querySelectorAll('#hsk-cands [data-a]')].map(b => b.dataset.a)")
        check(ch in cands, "the character drawn is among those offered", (ch, cands))
        ink = page.evaluate("""() => { const c = document.querySelector('#hsk-pad'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; }""")
        check(ink > 100, "the strokes drawn on the pad", ink)
        no_overflow(page, "writing by hand")
        shot(page, "hsk-caractere-main")
        if ch in cands:
            page.click('#hsk-cands [data-a="%s"]' % ch)
            page.wait_for_selector("#hsk-page .hsk-corr")
            check(page.inner_text("#hsk-page .hsk-verdict") == "Juste", "the character chosen is right")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-page .hsk-score")
        page.click('#hsk-page [data-hsk="home"]')

        print("mock exam")
        page.evaluate("() => { hsk.pace = 0.002; __said.length = 0; }")
        page.click('#hsk-home [data-hsk="exam"]')
        page.wait_for_selector("#hsk-page .hsk-n")
        run = page.evaluate("() => state.hskRun.pages.map(p => p.k).join(' ')")
        check(run.count("e2") == 10 and run.count("e3") == 10 and run.count("e4") == 10 and run.count("l1") == 2 and run.count("l2") == 2
              and run.count("l3") == 10 and run.count("w1") == 5 and run.count("w2") == 5, "70 questions in the order of the exam", run)
        check(nb(page.inner_text("#hsk-page .hsk-n")) == "Question 11", "numbered as in the HSK (from 11)", page.inner_text("#hsk-page .hsk-n"))
        c = page.evaluate(CUR)
        right_single(page, c)                         # question 11 right
        check(page.locator("#hsk-page .hsk-corr").count() == 0 and page.locator('#hsk-page [data-hsk="replay"]').count() == 0,
              "no correction, no replay in a mock exam")
        page.wait_for_function("() => state.hskRun.i >= 1", timeout=10000)
        texts = [s["text"] for s in page.evaluate("() => __said")]
        check(texts[:2] == [c["it"]["t"]["zh"]] * 2, "each recording twice, then the next question by itself", texts[:3])
        page.wait_for_function("() => state.hskRun.sec === 1", timeout=60000)
        page.evaluate("() => { hsk.pace = 1; state.hskRun.ends = Date.now() + 25 * 60e3; hskClock(); }")
        page.wait_for_selector("#hsk-clock:not([hidden])")
        check(page.inner_text("#hsk-clock").startswith("2"), "the reading's time left", page.inner_text("#hsk-clock"))
        check(nb(page.inner_text("#hsk-page .hsk-n")) == "Questions 41 à 45", "the reading from 41", page.inner_text("#hsk-page .hsk-n"))
        check(page.locator("#hsk-page .hsk-sheet button").count() == 14 and page.locator('#hsk-page [data-hsk="prev"]').is_disabled(),
              "the sheet of the reading's questions", page.locator("#hsk-page .hsk-sheet button").count())
        c = page.evaluate(CUR)
        for j in range(5):
            page.click('#hsk-page .hsk-letters [data-q="%d"][data-a="%d"]' % (j, j))
        check(page.locator("#hsk-page .hsk-sheet button.fait").count() == 1, "the page answered marked on the sheet")
        page.click('#hsk-page .hsk-sheet [data-go="%d"]' % (c["i"] + 4))   # a text of reading 3
        c = page.evaluate(CUR)
        check(c["k"] == "l3", "a question of the sheet opened", c["k"])
        right_single(page, c)
        no_overflow(page, "exam, reading")
        shot(page, "hsk-examen-lecture")
        # leaving the view pauses the exam, a reload keeps it
        page.click('.tab[data-view="words"]')
        paused = page.evaluate("() => [state.hskRun.pause, state.hskRun.left > 20 * 60e3, state.hskRun.ends]")
        check(paused[0] and paused[1] and paused[2] == 0, "another view: the exam waits, its time too", paused)
        page.reload()
        wait_ready(page)
        page.evaluate("() => { hsk.pace = 1; }")
        open_hsk(page)
        check(page.locator('#hsk-home [data-hsk="resume"]').count() == 1 and "Examen blanc en pause" in nb(page.inner_text("#hsk-home")),
              "after a reload: Reprendre l’examen blanc")
        page.click('#hsk-home [data-hsk="resume"]')
        page.wait_for_selector("#hsk-page .hsk-n")
        c2 = page.evaluate(CUR)
        check(c2["id"] == c["id"] and page.evaluate("() => state.hskRun.ends > Date.now() + 20 * 60e3"), "the same question, the time going on", c2["id"])
        page.click('#hsk-page [data-hsk="secdone"]')
        page.wait_for_selector("#hsk-sec-confirm .confirm")
        check("sans réponse" in page.inner_text("#hsk-sec-confirm"), "unanswered questions: asked first")
        page.click('#hsk-page [data-hsk="secdone-yes"]')
        page.wait_for_function("() => state.hskRun.sec === 2")
        check(nb(page.inner_text("#hsk-page .hsk-n")) == "Question 71", "the writing from 71", page.inner_text("#hsk-page .hsk-n"))
        c = page.evaluate(CUR)
        order = []
        rest = c["it"]["zh"].rstrip("。？！")
        while rest:
            b = next(i for i, x in enumerate(c["it"]["blocs"]) if rest.startswith(x) and i not in order)
            order.append(b)
            rest = rest[len(c["it"]["blocs"][b]):]
        for b in order:
            page.click('#hsk-page .bloc[data-in="%d"]' % b)
        page.evaluate("() => { state.hskRun.ends = Date.now() + 1500; }")
        page.wait_for_function("() => state.hskRun.done", timeout=10000)
        page.wait_for_selector("#hsk-page .hsk-score")
        e = page.evaluate("() => state.hskLog[0]")
        check(e["k"] == "exam" and len(e["pts"]) == 3 and len(e["ok"]) + len(e["ko"]) == 70, "the mock exam kept, its three notes", e.get("pts"))
        check(page.inner_text("#hsk-page .hsk-score b") == str(sum(e["pts"])) and "sur 300" in page.inner_text("#hsk-page .hsk-score"), "the score over 300")
        check(len(e["ok"]) >= 8, "the answers given count (11, 41-45, a text, 71)", len(e["ok"]))
        check(page.locator("#hsk-page table.dt tr").count() == 4 and page.locator("#hsk-page details.hsk-miss").count() > 10,
              "a line per section, the questions missed")
        no_overflow(page, "exam, end")
        shot(page, "hsk-examen-fin")
        page.click('#hsk-page [data-hsk="home"]')
        page.wait_for_selector("#hsk-home .hsk-log")
        check("Examen blanc" in page.inner_text("#hsk-home .hsk-log") and "/300" in page.inner_text("#hsk-home .hsk-log"), "the last results")

        print("storage and sync")
        merged = page.evaluate("""() => {
            const a = { start: 11, at: 12, k: 'e2', ok: ['e2-001'], ko: [] }, b = { start: 13, at: 14, k: 'exam', ok: [], ko: ['e2-002'], pts: [10, 20, 30] };
            const base = docOf(state), l = { ...clone(base), hskLog: { ...base.hskLog, 11: a } }, r = { ...clone(base), hskLog: { ...base.hskLog, 13: b } };
            const m = mergeDocs(base, l, r), old = clone(r); delete old.hskLog;
            const kept = mergeDocs(base, l, old);       // a device of a version from before: the results stay
            return [Object.keys(m.hskLog).includes('11') && Object.keys(m.hskLog).includes('13'), stateFromDoc(m, state).hskLog.some(e => e.start === 13),
                    !!kept.hskLog[11], 'hskRun' in docOf(state)]; }""")
        check(merged == [True, True, True, False], "results merged from both devices; the exercise in progress stays here", merged)
        clean = page.evaluate("""() => { const s = normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3], hskWrite: 'x' },
            hskLog: [{ start: 5, k: 'zz', ok: ['a'] }, { start: 6, k: 'e2', ok: ['e2-001'], ko: [] }, { start: 7, k: 'exam', ok: [], ko: ['x'], pts: [500, 'a'] }],
            hskRun: { kind: 'part', pages: [{ k: 'nope', id: 'x' }] } });
            return [s.hskLog.length, s.hskLog.find(e => e.k === 'exam').pts, s.hskRun, s.settings.hskWrite]; }""")
        check(clean == [2, [100, 0, 0], None, "main"], "normalizeState cleans the results and the exercise", clean)
        kept = page.evaluate("""() => { const s = normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3] },
            hskLog: [{ start: 5, k: 'w1', g: 'ba', ok: ['w1-002'], ko: [] }, { start: 6, k: 'e2', g: 'ba', ok: ['e2-001'], ko: [] }],
            hskRun: { kind: 'part', k: 'w1', g: 'ba', pages: [{ k: 'w1', id: 'w1-002', perm: [1, 0, 2, 3] }] } });
            return [s.hskLog.find(e => e.k === 'w1').g, 'g' in s.hskLog.find(e => e.k === 'e2'), s.hskRun.g]; }""")
        check(kept == ["ba", False, "ba"], "the fiche kept in the results and the exercise (writing 1 only)", kept)

        print("dark theme, computer")
        page.evaluate("() => { state.settings.theme = 'dark'; applyLook(state.settings); }")
        start_part(page, "l3")
        shot(page, "hsk-texte-sombre")
        page.click("#hsk-stop")
        page.wait_for_selector("#hsk-home .hsk-part")
        page.click('.hsk-part[data-fiche="bi"]')
        page.wait_for_selector("#sheet:not([hidden]) .fiche")
        shot(page, "hsk-fiche-sombre")
        page.keyboard.press("Escape")
        page.evaluate("() => { state.settings.theme = 'auto'; applyLook(state.settings); }")
        ctx.close()

        ctx, page = new_page(browser, errors, size=(1366, 768), mobile=False)
        ctx.add_init_script(VOICE)
        page.goto(url)
        wait_ready(page)
        open_hsk(page)
        cols = page.evaluate("() => getComputedStyle(document.querySelector('#hsk-home')).columnWidth")
        check(cols == "460px", "the home in columns on a computer", cols)
        shot(page, "hsk-ordinateur")
        page.click('.hsk-part[data-part="e4"]')
        page.wait_for_selector("#hsk-page .hsk-opt")
        page.keyboard.press("b")
        page.wait_for_selector("#hsk-page .hsk-corr")
        check(page.evaluate("() => state.hskRun.ans[state.hskRun.pages[0].id]") == page.evaluate("() => state.hskRun.pages[0].perm[1]"), "B on the keyboard answers B")
        page.keyboard.press("Enter")
        page.wait_for_function("() => state.hskRun.i === 1")
        check(True, "Entrée: the next question")
        w = page.evaluate("() => document.querySelector('#hsk-run').getBoundingClientRect().width")
        check(w <= 760, "the question no wider than 760 px", w)
        shot(page, "hsk-ordinateur-dialogue")

        print("offline")
        page.evaluate("() => navigator.serviceWorker.ready")
        page.wait_for_timeout(1500)
        ctx.set_offline(True)
        page.reload()
        wait_ready(page)
        open_hsk(page)
        page.wait_for_selector("#hsk-page .hsk-n, #hsk-home .hsk-part", timeout=10000)
        check(page.evaluate("() => !!HSK && HSK_BY.size > 100"), "the questions there offline")
        ctx.close()
        browser.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
