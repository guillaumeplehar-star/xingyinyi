# -*- coding: utf-8 -*-
"""Listes créées sur le téléphone, exemple sur les faces 形 (caractères) et 音 (pinyin, boutons Mot et Phrase),
publication sur GitHub (API simulée, avec le délai de mise en ligne de GitHub Pages ; la liste publiée garde la
progression de ses mots, seau compris, et la file n'a plus d'identifiant du téléphone), bouton de mise à jour.
Lancer depuis la racine du dépôt :  py tests\\test_listes.py
"""
import json
import os
import re
import unicodedata

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, nb


def squash(s):
    """Pinyin compared without the spacing of the spans (and with the app's apostrophe)."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", (s or "").replace("'", "’")))


# what the 音 face shows: the sentence's pinyin, its underlined part, the speak buttons
SOUND_JS = """(sel) => {
  const f = document.querySelector(sel), x = f.querySelector('.sound-ex'), m = x && x.querySelector('mark');
  return { text: x && x.textContent, tones: !!x && x.classList.contains('tones'),
    toned: x ? x.querySelectorAll('span.t1, span.t2, span.t3, span.t4, span.t5').length : 0,
    marks: x ? x.querySelectorAll('mark').length : 0, mark: m && m.textContent, markFold: m && fold(m.textContent),
    speaks: !!f.querySelector('.speaks'),
    btns: [...f.querySelectorAll('.speaks button')].map(b =>
      [b.hasAttribute('data-say-ex') ? 'ex' : b.hasAttribute('data-say') ? 'say' : '?', b.textContent.trim()]) };
}"""

# the 音 face fits: nothing taller than the face body, the sentence neither clipped nor squashed by the flex column
# (its overflow:hidden lets it shrink to nothing), the word's pinyin within its room, buttons of 34 px at least
FIT_JS = """(which) => {
  const p = which === 'sheet' ? sheetPrism : prism, f = p.faces[1], body = f.querySelector('.face-body'), x = f.querySelector('.sound-ex'), py = f.querySelector('.py');
  const need = [...body.children].reduce((a, el) => a + outer(el), 0);
  return { need: Math.round(need), room: body.clientHeight, sound: !!x, xfit: !x || x.scrollWidth <= x.clientWidth + 1,
    xH: x ? x.offsetHeight : null, xScrollH: x ? x.scrollHeight : null, xclip: !!x && x.scrollHeight > x.clientHeight + 1,
    wrap: !!x && x.classList.contains('wrap'), xs: x ? getComputedStyle(x).fontSize : null, pyfs: py.style.fontSize,
    pyfit: py.scrollWidth <= p.w - 44 + 1, btnH: [...f.querySelectorAll('.speaks button')].map(b => b.offsetHeight) };
}"""


def fits(m):
    return (m["sound"] and m["need"] <= m["room"] + 1 and m["xfit"] and not m["xclip"] and m["pyfit"]
            and all(h >= 34 for h in m["btnH"]))


def sound_face(page):
    """The current card's 音 face (study view), the 例 slip during a review, the switch, markPinyin."""
    # speechSynthesis is unreliable without a window: record what would be said instead
    page.evaluate("""() => { window.__said = []; tts.ok = true;
        tts.say = (text, btn) => { window.__said.push(text); return true; }; redrawCurrent(); }""")
    w = page.evaluate("() => { const w = BYID.get(study.cur); return { id: w.id, h: w.h, p: w.p, s: w.s || '', e: w.e || '', ep: w.ep || '', ef: w.ef || '' }; }")
    check(w["e"] and w["ep"] and w["ef"], "first card has an example, its pinyin and its translation", w)
    page.click("#turnbtn")
    page.wait_for_timeout(700)
    shot(page, "phone-01b-sound-example")
    face = page.evaluate("() => prism.face")
    snd = page.evaluate(SOUND_JS, "#stage .face[data-face='1']")
    word_fold = page.evaluate("(p) => fold(String(p).split('/')[0])", w["p"])
    # (a) the sentence in pinyin, the word's syllables underlined
    check(face == 1 and snd["text"] is not None and squash(snd["text"]) == squash(w["ep"]),
          "音 face: the sentence's pinyin under the word's", (face, snd["text"], w["ep"]))
    check(snd["tones"] and snd["toned"] >= len(w["ep"].split()), "音 face: the sentence's syllables coloured by tone", snd)
    check(snd["marks"] == 1 and snd["markFold"] == word_fold, "音 face: the word underlined in the sentence's pinyin",
          (snd["mark"], w["p"]))
    check(snd["btns"] == [["say", "Mot"], ["ex", "Phrase"]], "音 face: a button for the word and one for the sentence", snd["btns"])
    said = page.evaluate("() => [...window.__said]")
    check(said == [w["s"] or w["h"]], "turning to 音 reads the word, not the sentence", said)
    m = page.evaluate(FIT_JS, "study")
    check(fits(m), "音 face: sentence, pinyin and buttons fit in the face", m)
    # (b) the two buttons speak, and do not turn the card
    before = page.evaluate("() => ({ turns: prism.turns, cur: study.cur })")
    page.evaluate("() => { window.__said.length = 0; }")
    page.click("#stage .face[data-face='1'] [data-say-ex]")
    page.click("#stage .face[data-face='1'] [data-say]")
    after = page.evaluate("() => ({ said: [...window.__said], turns: prism.turns, face: prism.face, cur: study.cur, grades: !document.querySelector('#grades').hidden })")
    check(after["said"] == [w["e"], w["s"] or w["h"]], "Phrase reads the sentence, Mot reads the word (audio text first)", after["said"])
    check(after["turns"] == before["turns"] and after["face"] == 1 and after["cur"] == before["cur"] and after["grades"],
          "the speak buttons do not turn the card", (before, after))
    # (e) the 例 slip during a review: hanzi and translation only, the pinyin lives on the 音 face
    slip_js = """() => { const s = document.querySelector('#example'), t = s.querySelector('[data-ex-toggle]'), fr = s.querySelector('.ex-fr');
        return { covered: !!s.querySelector('.ex.covered'), py: s.querySelectorAll('.ex-py').length, zh: (s.querySelector('.ex-zh') || {}).textContent,
          toggle: t && t.textContent.trim(), expanded: t && t.getAttribute('aria-expanded'), fr: fr && fr.textContent,
          frShown: !!fr && fr.offsetHeight > 0, play: !!s.querySelector('[data-ex-say]') }; }"""
    sl = page.evaluate(slip_js)
    check(not sl["covered"] and sl["py"] == 0 and sl["zh"] == w["e"] and sl["play"], "例 slip in a review: the sentence in characters, no pinyin", sl)
    check(sl["toggle"] == "Traduction" and sl["expanded"] == "false" and not sl["frShown"], "例 slip: the toggle offers the translation only", sl)
    page.click("#example [data-ex-toggle]")
    page.wait_for_timeout(450)
    sl = page.evaluate(slip_js)
    check(sl["frShown"] and sl["fr"] == w["ef"] and sl["py"] == 0 and sl["toggle"] == "Masquer", "例 slip opened: the translation, still no pinyin", sl)
    shot(page, "phone-01c-slip-translation")
    page.click("#example [data-ex-toggle]")
    page.wait_for_timeout(300)
    sl = page.evaluate(slip_js)
    check(sl["toggle"] == "Traduction" and not sl["frShown"] and page.evaluate("() => state.settings.exDetails") is False,
          "例 slip closed again", sl)
    page.evaluate("() => { window.__said.length = 0; }")
    page.click("#example [data-ex-say]")
    check(page.evaluate("() => [...window.__said]") == [w["e"]], "the slip's speaker still reads the sentence")
    # no speech synthesis: no speak buttons, the sentence's pinyin still there
    st = page.evaluate("""() => { tts.ok = false; redrawCurrent(); const f = prism.faces[1];
        const r = { speaks: !!f.querySelector('.speaks'), btn: !!f.querySelector('[data-say], [data-say-ex]'), sound: !!f.querySelector('.sound-ex') };
        tts.ok = true; redrawCurrent(); return r; }""")
    check(st == {"speaks": False, "btn": False, "sound": True}, "without speech synthesis: no buttons, the pinyin still shown", st)
    # (d) the switch drives the sentence on both faces
    page.click('.tab[data-view="settings"]')
    lbl = nb(page.inner_text("#lbl-exform"))
    check("形" in lbl and "音" in lbl, "switch label names the 形 and 音 faces", lbl)
    check(nb(page.inner_text("#lbl-ex")) == "Traduction des exemples", "second switch: translation only", page.inner_text("#lbl-ex"))
    faces_js = """() => ({ on: state.settings.exOnForm, aria: document.querySelector('#sw-exform').getAttribute('aria-checked'),
        saved: JSON.parse(localStorage.getItem('xingyinyi.v2')).settings.exOnForm,
        form: !!prism.faces[0].querySelector('.form-ex'), sound: !!prism.faces[1].querySelector('.sound-ex'),
        btns: prism.faces[1].querySelectorAll('.speaks button').length })"""
    page.click("#sw-exform")
    off = page.evaluate(faces_js)
    check(off == {"on": False, "aria": "false", "saved": False, "form": False, "sound": False, "btns": 2},
          "switch off: no sentence on 形 nor on 音, both buttons kept", off)
    page.click("#sw-exform")
    on = page.evaluate(faces_js)
    check(on == {"on": True, "aria": "true", "saved": True, "form": True, "sound": True, "btns": 2},
          "switch on again: the sentence back on 形 and 音", on)
    page.click('.tab[data-view="study"]')
    page.wait_for_timeout(300)
    m = page.evaluate(FIT_JS, "study")
    check(fits(m), "音 face laid out again after the settings", m)
    # the longest sentence on a small phone (320 × 568) and on this one
    longest = page.evaluate("() => DECK.filter(w => w.ep).sort((a, b) => b.ep.length - a.ep.length || b.p.length - a.p.length)[0].id")
    for size in ((320, 568), (390, 844)):
        page.set_viewport_size({"width": size[0], "height": size[1]})
        page.wait_for_timeout(400)
        page.evaluate("(id) => prism.show(BYID.get(id), 1)", longest)
        m = page.evaluate(FIT_JS, "study")
        check(fits(m), "音 face, longest sentence (%s), %d × %d: everything fits" % (longest, size[0], size[1]), m)
        shot(page, "phone-01d-sound-longest-%d" % size[0])
    page.evaluate("() => redrawCurrent()")
    # (g) markPinyin
    cases = [
        ("Wǒ yào dǎyìn zhè zhāng zhàopiàn.", "dǎyìn", ["dǎyìn"], "plain word"),
        ("Nǐ kàn yíxià zhège.", "yíxià", ["yíxià"], "一 with the same tone"),
        ("Nǐ kàn yīxià zhège.", "yíxià", ["yīxià"], "一 with another tone in the sentence"),
        ("Wǒ bù hē kāfēi.", "bú", ["bù"], "不 with another tone in the sentence"),
        ("Nǐ kàn yíxià zhège.", "yi2xia4", ["yíxià"], "word pinyin written with digits"),
        ("Wǒ huì shuō yìdiǎnr Hànyǔ.", "yìdiǎnr", ["yìdiǎnr"], "erhua"),
        ("Xièxie nǐ! – Bú kèqi.", "bú kèqi", ["Bú kèqi"], "two syllables across a space, capital letter"),
        ("Tā nǚ'ér hěn piàoliang.", "nǚ'ér", ["nǚ’ér"], "apostrophe inside the word"),
        ("Wǒ jiā zhǐyǒu yì zhī māo.", "zhǐ / zhī", ["zhǐ"], "two readings: the first one"),
        ("Wǒ yǒu yí ge gēge.", "gè", ["ge"], "neutral tone in the sentence"),
        ("Wǒ bù hē kāfēi.", "chá", [], "word absent from the sentence"),
        ("Wǒ xǐhuan tā.", "huā", [], "whole syllables only (huā is not inside huan)"),
        ("Nǐ hǎo.", "", [], "no word pinyin"),
        ("Tā shuō <hǎo>.", "hǎo", ["hǎo"], "escaped markup"),
    ]
    res = page.evaluate("""(cases) => cases.map(([ep, p]) => { const d = document.createElement('div'); d.innerHTML = markPinyin(ep, p);
        const m = d.querySelector('mark');
        return { text: d.textContent, marks: [...d.querySelectorAll('mark')].map(x => x.textContent), html: d.innerHTML,
          before: m ? d.textContent.slice(0, d.textContent.indexOf(m.textContent)) : null }; })""",
                        [[c[0], c[1]] for c in cases])
    bad = []
    for (ep, p, want, label), r in zip(cases, res):
        if r["marks"] != want or r["text"] != ep.replace("'", "’"):
            bad.append((label, p, r["marks"], r["text"]))
    check(not bad, "markPinyin: the word's syllables underlined, tones ignored (%d cases)" % len(cases), bad)
    check('<mark><span class="t3">dǎ</span><span class="t4">yìn</span></mark>' in res[0]["html"], "markPinyin: tone classes kept inside the mark", res[0]["html"])
    check(res[9]["before"] == "Wǒ yǒu yí ", "markPinyin: the first matching syllable (ge, not the gē of gēge)", res[9]["before"])
    check("&lt;" in res[13]["html"], "markPinyin escapes the sentence", res[13]["html"])
    # with the sentence in characters: placed by position (a homophone before the word is left alone), every occurrence
    placed = page.evaluate("""(ids) => ids.map(id => { const w = BYID.get(id), d = document.createElement('div');
        d.innerHTML = markPinyin(w.ep, w.p, w.e, w.h); const m = [...d.querySelectorAll('mark')];
        return [id, m.map(x => x.textContent),
          d.innerHTML.split('<mark>')[0].replace(/<[^>]+>/g, '')]; })""", ["hsk2:药", "hsk3:站", "hsk3:只", "hsk3:还"])
    check(placed[0][1] == ["yào"] and placed[0][2] == "Nǐ shēngbìng le, yào chī ", "markPinyin: 药 underlined, not the yào of 要 before it", placed[0])
    check(placed[1][1] == ["zhàn", "zhàn"], "markPinyin: every occurrence underlined, like the characters (站)", placed[1])
    check(placed[2][1] == ["zhǐ", "zhī"], "markPinyin: both readings of 只 underlined where they are", placed[2])
    whole = page.evaluate("""() => DECK.filter(w => w.ep).map(w => { const d = document.createElement('div');
        d.innerHTML = markPinyin(w.ep, w.p, w.e, w.h); return [w.id, d.querySelectorAll('mark').length, w.e.split(w.h).length - 1]; })
        .filter(([id, n, want]) => n !== want)""")
    check(not whole, "every example of the lists underlines its word in pinyin, as often as in characters", whole[:10])


def sound_face_sheets(page):
    """The word sheets (Mots tab): a phone word without example, one without pinyin for its sentence, a HSK word."""
    pid = page.evaluate("() => wdeck")
    open_js = """(h) => { const w = DECK.find(x => x.h === h && (x.deck === wdeck || wdeck === 'all'));
        return { id: w.id, e: w.e || '', ep: w.ep || '', ef: w.ef || '', p: w.p, s: w.s || '', h: w.h }; }"""
    sheet_js = """() => { const b = document.querySelector('#sheet-body'), s = document.querySelector('#sheet-ex'), py = s.querySelector('.ex-py');
        const m = py && py.querySelector('mark');
        return { py: py && py.textContent, mark: m && m.textContent, fr: !!s.querySelector('.ex-fr'), toggle: !!s.querySelector('[data-ex-toggle]'),
          empty: !!s.querySelector('.ex.empty') }; }"""
    # (c) a word without example: one button, no sentence
    page.click('#wlist .wrow:has-text("复印")')
    page.wait_for_selector("#sheet:not([hidden]) #sheet-stage .face[data-face='1']")
    w = page.evaluate(open_js, "复印")
    snd = page.evaluate(SOUND_JS, "#sheet-stage .face[data-face='1']")
    check(not w["e"] and snd["text"] is None and snd["btns"] == [["say", "Écouter"]],
          "word without example: a single Écouter button, no sentence on 音", (w, snd))
    page.click("#sheet .close")
    # a sentence without its pinyin: both buttons, no pinyin line
    page.click('#wlist .wrow:has-text("打印")')
    page.wait_for_selector("#sheet:not([hidden]) #sheet-stage .face[data-face='1']")
    w = page.evaluate(open_js, "打印")
    snd = page.evaluate(SOUND_JS, "#sheet-stage .face[data-face='1']")
    sh = page.evaluate(sheet_js)
    check(w["e"] and not w["ep"] and snd["text"] is None and snd["btns"] == [["say", "Mot"], ["ex", "Phrase"]] and sh["py"] is None,
          "sentence without its pinyin: Mot and Phrase, no pinyin line", (w, snd, sh))
    page.evaluate("() => { window.__said.length = 0; }")
    page.click("#sheet-stage")                         # turn the sheet's card to 音
    page.wait_for_timeout(700)
    page.evaluate("() => { window.__said.length = 0; }")
    page.click("#sheet-stage .face[data-face='1'] [data-say-ex]")
    r = page.evaluate("() => ({ said: [...window.__said], face: sheetPrism.face })")
    check(r == {"said": [w["e"]], "face": 1}, "word sheet: Phrase reads the sentence without turning the card", r)
    page.click("#sheet .close")
    # (f) the word sheet of a HSK word keeps the sentence's pinyin under the characters
    page.click('#wdeck button[data-deck="hsk3"]')
    page.click('#wlist .wrow[data-id="hsk3:还"]')
    page.wait_for_selector("#sheet:not([hidden]) #sheet-ex .ex-py")
    w = page.evaluate("() => { const w = BYID.get('hsk3:还'); return { ep: w.ep, p: w.p }; }")
    sh = page.evaluate(sheet_js)
    snd = page.evaluate(SOUND_JS, "#sheet-stage .face[data-face='1']")
    check(sh["py"] is not None and squash(sh["py"]) == squash(w["ep"]) and sh["mark"] == w["p"] and sh["fr"] and not sh["toggle"],
          "word sheet: the sentence with its pinyin (word underlined) and its translation", sh)
    check(squash(snd["text"]) == squash(w["ep"]) and snd["btns"] == [["say", "Mot"], ["ex", "Phrase"]],
          "word sheet: the 音 face carries the sentence's pinyin too", snd)
    m = page.evaluate(FIT_JS, "sheet")
    check(fits(m), "word sheet: the 音 face fits in the smaller card", m)
    shot(page, "phone-02a-word-sheet")
    page.click("#sheet .close")
    page.click('#wdeck button[data-deck="%s"]' % pid)


def main():
    errors = []
    site = fresh_copy("site-phone")
    global ORIG_H3
    ORIG_H3 = open(os.path.join(site, "decks", "hsk3.tsv"), encoding="utf-8").read()
    httpd, url = serve(site)
    calls = []
    repo = {}
    for folder, _, names in os.walk(os.path.join(site, "decks")):
        for n in names:
            full = os.path.join(folder, n)
            repo[os.path.relpath(full, site).replace(os.sep, "/")] = open(full, encoding="utf-8").read()

    def deploy():
        for path, content in repo.items():
            # newline="": the files served must be byte for byte what was published (no \r\n on Windows)
            open(os.path.join(site, *path.split("/")), "w", encoding="utf-8", newline="").write(content)
        for n in os.listdir(os.path.join(site, "decks")):
            if "decks/" + n not in repo:
                os.remove(os.path.join(site, "decks", n))

    def api(route):
        req = route.request
        u = req.url.split("api.github.com", 1)[1]
        calls.append((req.method, u, req.post_data))
        path = u.split("?")[0]
        def ok(obj):
            route.fulfill(status=200, content_type="application/json", body=json.dumps(obj))
        if path == "/repos/u/xingyinyi":
            return ok({"default_branch": "main", "permissions": {"push": True}})
        if path == "/repos/u/xingyinyi/git/ref/heads/main":
            return ok({"object": {"sha": "c0"}})
        if path == "/repos/u/xingyinyi/git/commits/c0":
            return ok({"tree": {"sha": "t0"}})
        m = re.match(r"/repos/u/xingyinyi/contents/(.+)$", path)
        if m:
            if m.group(1) in repo:
                return route.fulfill(status=200, content_type="text/plain; charset=utf-8", body=repo[m.group(1)])
            return route.fulfill(status=404, content_type="application/json", body='{"message":"Not Found"}')
        if path.endswith("/git/trees"):
            for e in json.loads(req.post_data)["tree"]:
                if e.get("sha", "x") is None:
                    repo.pop(e["path"], None)
                else:
                    repo[e["path"]] = e["content"]
            return ok({"sha": "t1"})
        if path.endswith("/git/commits"):
            return ok({"sha": "c1"})
        if path.endswith("/git/refs/heads/main"):
            return ok({"object": {"sha": "c1"}})
        route.fulfill(status=500, body="unexpected")

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx, page = new_page(b, errors)
        page.route("https://api.github.com/**", api)
        page.goto(url)
        wait_ready(page)
        # example on the 形 face
        fx = page.evaluate("() => { const f = document.querySelector('#stage .face[data-face=\"0\"] .form-ex'); return f ? f.textContent : null; }")
        w = page.evaluate("() => BYID.get(study.cur).e || null")
        check((fx is not None) == (w is not None) and (fx is None or fx == w), "example sentence on the 形 face", (fx, w))
        shot(page, "phone-01-form-example")
        sound_face(page)
        # create a list, add two words into it
        page.click('.tab[data-view="words"]')
        page.click("#wdeck [data-newlist]")
        page.fill("#l-n", "Cours du mardi")
        page.click("#lform button[type=submit]")
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ lists: state.lists.map(x => x.nom), wdeck })")
        check(st["lists"] == ["Cours du mardi"] and st["wdeck"].startswith("p-"), "list created and selected", st)
        page.click('#listbar [data-la="add"]')
        page.fill("#f-h", "复印")
        page.fill("#f-p", "fu4yin4")
        page.fill("#f-f", "photocopier")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        page.click("#btn-add")
        page.fill("#f-h", "打印")
        page.fill("#f-p", "dǎyìn")
        page.fill("#f-f", "imprimer")
        page.click(".more summary")
        page.fill("#f-e", "我要打印这张照片。")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        shot(page, "phone-02-list")
        page.click("#btn-add")
        page.fill("#f-h", "图书馆")
        page.fill("#f-p", "túshūguǎn")
        page.fill("#f-f", "bibliothèque")
        page.wait_for_timeout(100)
        check("Aussi dans HSK 3" in page.inner_text("#f-hh"), "hint: also in HSK 3")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ inList: LISTBYID.get(wdeck).words.map(w => w.h) })")
        check(st["inList"] == ["复印", "打印", "图书馆"], "words added to the new list (a HSK word included)", st)
        page.click("#btn-export")
        page.wait_for_timeout(200)
        exp = page.inner_text("#sheet-body")
        check("nouvelle-liste cours-du-mardi" in exp and "decks/cours-du-mardi.tsv" in exp, "export explains where the lines go", exp[:300])
        page.click("#sheet .close")
        sound_face_sheets(page)
        # a word in a second list via the form's "new list" option, then delete that list
        page.click("#btn-add")
        page.select_option("#f-l", "__new")
        page.fill("#f-ln", "À jeter")
        page.fill("#f-h", "安排")
        page.fill("#f-p", "an1pai2")
        page.fill("#f-f", "organiser")
        page.click("#wform button[type=submit]")
        page.wait_for_timeout(200)
        jid = page.evaluate("() => state.lists.find(x => x.nom === 'À jeter').id")
        page.click('#wdeck button[data-deck="%s"]' % jid)
        page.click('#listbar [data-la="delete"]')
        page.click('#listbar [data-la="delete-yes"]')
        page.wait_for_timeout(200)
        st = page.evaluate("() => ({ lists: state.lists.map(x => x.nom), words: state.custom.map(w => w.h) })")
        check(st == {"lists": ["Cours du mardi"], "words": ["复印", "打印", "图书馆"]}, "list deleted with its words", st)
        # learn one of them, edit a HSK word
        page.evaluate("() => { const w = state.custom.find(x => x.h === '打印'); applyGrade(w.id, true); state.edits['hsk3:还'] = { f: 'rendre ; rembourser' }; save(); rebuildDeck(); }")
        # connect to GitHub and publish
        page.click('.tab[data-view="settings"]')
        page.fill("#gh-repo", "u/xingyinyi")
        page.fill("#gh-token", "github_pat_test")
        page.click('[data-gh="login"]')
        page.wait_for_selector('[data-gh="publish"]')
        shot(page, "phone-03-github", full=False)
        page.click('[data-gh="publish"]')
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('Publié')", timeout=8000)
        msg = page.inner_text("#toast")
        print("  toast:", msg)
        tree = [json.loads(c[2]) for c in calls if c[0] == "POST" and c[1].endswith("/git/trees")][0]
        files = {e["path"]: e.get("content") for e in tree["tree"]}
        cfg = json.loads(files["decks/decks.json"])
        new = [l for l in cfg["listes"] if l["nom"] == "Cours du mardi"]
        check(tree["base_tree"] == "t0" and new and new[0]["fichier"] == "cours-du-mardi.tsv" and cfg["listes"][0]["nom"] == "Cours du mardi",
              "new list declared first in decks.json", cfg["listes"][:2])
        check(new and set(new[0]) == {"id", "nom", "fichier", "actif"}, "new decks.json entry without mode nor parJour", new)
        body = files.get("decks/cours-du-mardi.tsv", "")
        check("复印\tfùyìn\tphotocopier" in body and "打印\tdǎyìn\timprimer\t\t\t我要打印这张照片。" in body and "图书馆\ttúshūguǎn" in body and body.startswith("# 形音义"), "list file written", body[-200:])
        h3 = files.get("decks/hsk3.tsv", "")
        check("\trendre ; rembourser\t" in h3 and h3.count("\n") == ORIG_H3.count("\n"),
              "correction written into hsk3.tsv, nothing else touched")
        patch = [c for c in calls if c[0] == "PATCH"]
        check(patch and json.loads(patch[0][2])["sha"] == "c1", "branch moved to the new commit")
        after = page.evaluate("() => ({ lists: state.lists.length, custom: state.custom.length, card: state.cards['cours-du-mardi:打印'], edits: Object.keys(state.edits).length, list: LISTBYID.get('cours-du-mardi') && LISTBYID.get('cours-du-mardi').words.length })")
        check(after["lists"] == 0 and after["custom"] == 0 and after["card"] and after["card"]["b"] == 1 and after["edits"] == 0 and after["list"] == 3,
              "phone list became a repo list, progress kept (bucket 1)", after)
        ln = page.evaluate("""() => { const L = [study.cur, ...study.queue].filter(Boolean);
            return { stale: L.filter(id => /^(u-|p-)/.test(id)), cards: Object.keys(state.cards).filter(id => /^(u-|p-)/.test(id)),
              fresh: ['复印', '图书馆'].map(h => L.includes('cours-du-mardi:' + h)), learnt: L.includes('cours-du-mardi:打印') }; }""")
        check(ln == {"stale": [], "cards": [], "fresh": [True, True], "learnt": False},
              "line after the merge: no phone id left, the published words waiting for their first pass", ln)
        # GitHub Pages has not deployed yet: the old files must not undo the publication
        page.evaluate("() => refreshLists(false, true)")
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('pas encore')", timeout=8000)
        st = page.evaluate("() => ({ list: !!LISTBYID.get('cours-du-mardi'), f: BYID.get('hsk3:还').f })")
        check(st["list"] and "rembourser" in st["f"], "stale GitHub Pages ignored after publishing", st)
        deploy()
        page.evaluate("() => refreshLists(false, true)")
        page.wait_for_timeout(800)
        st = page.evaluate("() => ({ list: !!LISTBYID.get('cours-du-mardi'), guard: localStorage.getItem('xingyinyi.publie') })")
        check(st["list"] and st["guard"] is None, "deployed files accepted, guard cleared", st)
        # delete a repo list from the phone
        page.click('[data-gdel="cours-du-mardi"]')
        page.click('[data-gdel-yes="cours-du-mardi"]')
        page.wait_for_function("() => !LISTBYID.has('cours-du-mardi')", timeout=8000)
        deploy()
        tree2 = [json.loads(c[2]) for c in calls if c[0] == "POST" and c[1].endswith("/git/trees")][-1]
        dele = [e for e in tree2["tree"] if e.get("sha", "x") is None]
        check(dele and dele[0]["path"] == "decks/cours-du-mardi.tsv", "repo list deleted from the phone", tree2["tree"])
        # app update button
        page.click("#app-update")
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('à jour')", timeout=8000)
        check(True, "update button answers")
        shot(page, "phone-04-settings")
        ctx.close()
        b.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
