# -*- coding: utf-8 -*-
"""Affichage : thèmes (Automatique, Cahier, Papier blanc, Sépia, Contraste élevé, Tableau noir, Nuit), appliqués avant
le premier affichage, barre du navigateur ; taille du texte ; police des caractères ; grille des cases ; pinyin en
chiffres ; couleurs des tons (appli, Pleco, MDBG, aucune) ; animations ; liste des mots compacte ; réglages d'exemples
déplacés depuis Réglages ; réglages propres à l'appareil (synchronisation) ; valeurs inconnues ; téléphone et ordinateur.
Lancer depuis la racine du dépôt :  py tests\\test_affichage.py
"""
from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, nb

BG = {"light": "#e6ece4", "paper": "#efefed", "sepia": "#e8dcc4", "contrast": "#e8e8e8", "dark": "#131c17", "night": "#000000"}
LOOK_JS = """() => { const r = document.documentElement, cs = getComputedStyle(r);
    return { theme: r.dataset.theme || null, mode: r.dataset.mode, bg: cs.getPropertyValue('--bg').trim(), scheme: cs.colorScheme,
             metas: [...document.querySelectorAll('meta[name="theme-color"]')].map(m => m.content),
             saved: JSON.parse(localStorage.getItem('xingyinyi.v2')).settings.theme }; }"""
# a page wider than the screen (a text too large for its box) scrolls sideways: none of that
OVERFLOW = "() => { const m = document.querySelector('#main'); return m.scrollWidth - m.clientWidth; }"
# the theme as the page is parsed, before the app's script at the end of the body runs
EARLY = """new MutationObserver((ms, o) => { if (document.body) { window.__early = document.documentElement.dataset.theme || null; o.disconnect(); } })
    .observe(document, { childList: true, subtree: true });"""
PYTEXT = """(p) => { const d = document.createElement('div'); d.innerHTML = pinyinHTML(p); return d.textContent; }"""
# labels cut off in a choice (white-space, overflow: hidden): none
CUT = """() => [...document.querySelectorAll('.seg button')].filter(b => b.offsetParent && b.scrollWidth > b.clientWidth + 1).map(b => b.textContent.trim())"""


def rgb(h):
    return "rgb(%d, %d, %d)" % tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def view(page, name):
    page.click('.tab[data-view="%s"]' % name)
    page.wait_for_timeout(200)


def pick(page, look, v):                  # a choice of Affichage
    page.click('#view-display [data-look="%s"] [data-v="%s"]' % (look, v))


def css(page, sel, prop):
    return page.evaluate("([s, p]) => getComputedStyle(document.querySelector(s))[p]", [sel, prop])


def main():
    site = fresh_copy("site-affichage")
    httpd, url = serve(site)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ------------------------------------------------------------ the phone
        print("== téléphone")
        ctx, page = new_page(browser, errors)
        page.add_init_script(EARLY)
        page.goto(url)
        wait_ready(page)
        tabs = page.evaluate("() => [...document.querySelectorAll('.tab')].map(t => t.dataset.view)")
        check(tabs == ["study", "words", "progress", "display", "settings"], "a fifth tab, Affichage, before Réglages", tabs)
        bar = page.evaluate("() => [...document.querySelectorAll('.tab')].map(t => { const b = t.getBoundingClientRect(); return [b.left, b.right, t.scrollWidth <= t.clientWidth]; })")
        check(all(b[2] for b in bar) and bar[-1][1] <= 390, "the five tabs fit the phone's width", bar)
        look = page.evaluate(LOOK_JS)
        check(look["theme"] is None and look["mode"] == "light" and look["bg"] == BG["light"] and look["metas"] == ["#e6ece4", "#131c17"],
              "by default: Automatique, the device's light (Cahier)", look)
        view(page, "display")
        names = page.evaluate("() => [...document.querySelectorAll('#themes .theme')].map(b => [b.dataset.v, b.getAttribute('aria-checked'), b.querySelector('.nm').textContent])")
        check([n[0] for n in names] == ["auto", "light", "paper", "sepia", "contrast", "dark", "night"] and names[0][1] == "true"
              and [n[2] for n in names][2:5] == ["Papier blanc", "Sépia", "Contraste élevé"], "seven themes, Automatique chosen", names)
        moved = page.evaluate("""() => ({ here: ['#sw-exform', '#sw-ex', '#tone-legend'].every(s => document.querySelector('#view-display ' + s)),
            gone: !document.querySelector('#view-settings #sw-exform, #view-settings #sw-ex, #sw-tones'),
            voice: !!document.querySelector('#view-settings #sw-auto') && [...document.querySelectorAll('#view-settings .group-title')].some(t => t.textContent === 'Voix') })""")
        check(moved == {"here": True, "gone": True, "voice": True}, "the display settings of Réglages › Cartes moved here; Réglages keeps Voix", moved)
        shot(page, "aff-01-auto")

        # ---- each theme
        for t in ("light", "paper", "sepia", "contrast", "dark", "night"):
            page.click('#themes [data-v="%s"]' % t)
            look = page.evaluate(LOOK_JS)
            dark = t in ("dark", "night")
            check(look["theme"] == t and look["bg"] == BG[t] and look["mode"] == ("dark" if dark else "light") and look["scheme"] == ("dark" if dark else "light")
                  and look["metas"] == [BG[t], BG[t]] and look["saved"] == t, "theme %s: its colours, the browser's bar, saved" % t, look)
            check(page.get_attribute('#themes [data-v="%s"]' % t, "aria-checked") == "true", "theme %s: shown as chosen" % t)
            shot(page, "aff-02-theme-" + t)
            view(page, "study")
            if page.is_visible("#turnbtn"):
                page.click("#turnbtn")
                page.wait_for_timeout(650)
            shot(page, "aff-03-carte-" + t)
            view(page, "display")
        sw = page.evaluate("() => getComputedStyle(document.querySelector('#themes [data-v=\"sepia\"] .swp')).backgroundColor")
        check(sw == rgb(BG["sepia"]), "each swatch in its own theme's colours (here Sépia, the page in Nuit)", sw)

        # ---- the device's dark: Automatique follows it, a chosen theme does not
        page.click('#themes [data-v="auto"]')
        page.emulate_media(color_scheme="dark")
        page.wait_for_function("() => document.documentElement.dataset.mode === 'dark'", timeout=3000)
        look = page.evaluate(LOOK_JS)
        check(look["theme"] is None and look["mode"] == "dark" and look["bg"] == BG["dark"] and look["metas"] == ["#e6ece4", "#131c17"],
              "Automatique in a dark device: Tableau noir, the browser's bars as before", look)
        page.click('#themes [data-v="paper"]')
        look = page.evaluate(LOOK_JS)
        check(look["bg"] == BG["paper"] and look["mode"] == "light" and look["scheme"] == "light", "Papier blanc in a dark device: still white", look)
        page.emulate_media(color_scheme="light")

        # ---- kept, and set before the first paint
        page.click('#themes [data-v="sepia"]')
        page.reload()
        wait_ready(page)
        early = page.evaluate("() => window.__early")
        check(early == "sepia" and page.evaluate(LOOK_JS)["bg"] == BG["sepia"], "after a reload: Sépia, set as soon as the page is read", early)
        view(page, "display")

        # ---- text size
        page.click('[data-look="textSize"] [data-v="xl"]')
        tz = page.evaluate("() => [document.documentElement.style.getPropertyValue('--tz'), getComputedStyle(document.body).fontSize]")
        check(tz == ["1.25", "20px"], "Très grand: the text 25 % larger", tz)
        head = page.evaluate("""() => { const b = document.querySelector('.brand').getBoundingClientRect(), t = document.querySelector('.top');
            return { oneLine: b.height < 40, fits: t.scrollWidth <= t.clientWidth, words: getComputedStyle(document.querySelector('.startface .w')).display,
                     tab: getComputedStyle(document.querySelector('.tab')).fontSize }; }""")
        check(head == {"oneLine": True, "fits": True, "words": "none", "tab": "12px"},
              "Très grand: the header and the menu as they were, « D’abord » with 形 音 义 alone", head)
        widths = {}
        for v in ("study", "words", "progress", "display", "settings"):
            view(page, v)
            widths[v] = page.evaluate(OVERFLOW)
        check(all(x <= 0 for x in widths.values()), "Très grand on the phone: nothing wider than the screen", widths)
        cut = []
        for v in ("display", "study"):
            view(page, v)
            cut += page.evaluate(CUT)
        page.set_viewport_size({"width": 375, "height": 667})
        page.wait_for_timeout(300)
        tall = page.evaluate("() => { const m = document.querySelector('#main'); return m.scrollHeight - m.clientHeight; }")
        cut += page.evaluate(CUT)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        check(not cut and tall <= 0, "Très grand: every choice's label whole; the review fits a 375 × 667 phone", [cut, tall])
        view(page, "words")
        check(css(page, "#wlist .wrow .p", "fontSize") == "18.75px", "Très grand: the list's pinyin 15 → 18.75 px", css(page, "#wlist .wrow .p", "fontSize"))
        shot(page, "aff-04-mots-tres-grand")
        view(page, "study")
        shot(page, "aff-05-carte-tres-grand")
        view(page, "display")
        page.click('[data-look="textSize"] [data-v="s"]')
        view(page, "words")
        fs = [css(page, "#wlist .wrow .p", "fontSize"), css(page, ".searchbar input", "fontSize")]
        check(fs == ["13.5px", "16px"], "Petit: smaller texts, the search field still 16 px (no zoom in Safari)", fs)
        view(page, "display")
        page.click('[data-look="textSize"] [data-v="m"]')
        page.set_viewport_size({"width": 320, "height": 640})
        page.wait_for_timeout(300)
        cut = page.evaluate(CUT)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(300)
        check(not cut, "a 320 px phone: every label whole", cut)

        # ---- the characters' font
        fonts = {}
        for v in ("hei", "song", "kai"):
            pick(page, "zhFont", v)
            fonts[v] = [css(page, sel, "fontFamily").split(",")[0].strip('"') for sel in ("#look-sample .tzg span", ".brand")]
        check(fonts == {"hei": ["PingFang SC", "WK"], "song": ["Songti SC", "WK"], "kai": ["WK", "WK"]},
              "Hei, Song, Kai: the characters in that font, the app's name always in WenKai", fonts)
        lack = page.evaluate("""() => { const r = document.documentElement;
            r.style.setProperty('--zh-song', '"PasDePoliceIci"'); fontsHere.clear(); renderDisplay();
            const out = { off: document.querySelector('[data-look="zhFont"] [data-v="song"]').disabled, note: document.querySelector('#zh-note').textContent,
                          kai: document.querySelector('[data-look="zhFont"] [data-v="kai"]').disabled };
            r.style.removeProperty('--zh-song'); fontsHere.clear(); renderDisplay(); return out; }""")
        check(lack["off"] and not lack["kai"] and "Song" in lack["note"], "a font missing on the device (Song on the iPhone): its choice disabled, said", lack)

        # ---- the grid of the cells
        grids = {}
        for v in ("mi", "none", "tian"):
            pick(page, "grid", v)
            grids[v] = [css(page, "#look-sample .tzg .mzg", "display"), css(page, "#look-sample .tzg", "backgroundImage") != "none"]
        check(grids == {"mi": ["block", True], "none": ["none", False], "tian": ["none", True]},
              "米字格: the diagonals too; Sans guides: none; 田字格: the cross only", grids)

        # ---- pinyin in numbers
        page.click("#sw-pynum")
        cases = {s: page.evaluate(PYTEXT, s) for s in ("nǐ hǎo", "māma", "xī'ān", "nǚ'ér", "yíhuìr", "Wǒ zìjǐ zuò fàn.")}
        check(cases == {"nǐ hǎo": "ni3 hao3", "māma": "ma1 ma", "xī'ān": "xi1 an1", "nǚ'ér": "nü3 er2", "yíhuìr": "yi2 huir4",
                        "Wǒ zìjǐ zuò fàn.": "Wo3 zi4 ji3 zuo4 fan4."},
              "pinyin in numbers: the tone after each syllable (none for the neutral one), ü kept, 儿 glued", cases)
        sample = nb(page.inner_text("#look-sample .py"))
        view(page, "study")
        card = page.evaluate("() => [prism.faces[1].querySelector('.py').textContent, (prism.faces[1].querySelector('.sound-ex') || {}).textContent || '']")
        view(page, "words")
        row = nb(page.inner_text("#wlist .wrow .p"))
        marks = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
        check(sample == "ni3 hao3" and all(not any(c in x for c in marks) and any(c.isdigit() for c in x) for x in card + [row]),
              "in numbers on the card (word and sentence), in the list and in the sample", [sample, card, row])
        view(page, "display")
        page.click("#sw-pynum")
        check(nb(page.inner_text("#look-sample .py")) == "nǐ hǎo", "the tone marks again", page.inner_text("#look-sample .py"))

        # ---- tone colours
        view(page, "study")
        if page.is_visible("#turnbtn"):
            page.click("#turnbtn")
            page.wait_for_timeout(650)
        view(page, "display")
        pick(page, "tones", "pleco")
        view(page, "study")
        kept = page.evaluate("() => [prism.seen.size, !document.querySelector('#grades').hidden]")
        check(kept == [2, True], "a palette chosen: the card on screen stays turned, its answers shown", kept)
        view(page, "display")
        t2 = css(page, "#tone-legend .t2", "color")
        page.click('#themes [data-v="night"]')
        t2n = css(page, "#tone-legend .t2", "color")
        pick(page, "tones", "mdbg")
        t3n = css(page, "#tone-legend .t3", "color")
        page.click('#themes [data-v="sepia"]')
        t3 = css(page, "#tone-legend .t3", "color")
        check([t2, t2n, t3n, t3] == [rgb("#1d6626"), rgb("#7fd88a"), rgb("#7fd88a"), rgb("#1d6626")],
              "Pleco: 2 green; MDBG: 3 green; lighter in a dark theme, darker in Sépia (4.5 : 1)", [t2, t2n, t3n, t3])
        pick(page, "tones", "none")
        off = page.evaluate("""() => ({ on: state.settings.toneColors, legend: document.querySelector('#tone-legend').classList.contains('tones'),
            card: prism.faces[1].querySelector('.py').classList.contains('tones'), checked: document.querySelector('[data-look="tones"] [data-v="none"]').getAttribute('aria-checked') })""")
        check(off == {"on": False, "legend": False, "card": False, "checked": "true"}, "Aucune: no colours (the old switch off)", off)
        pick(page, "tones", "app")
        check(page.evaluate("() => [state.settings.toneColors, state.settings.tonePalette]") == [True, "app"], "Appli: the colours again")

        # ---- motion
        pick(page, "motion", "reduce")
        red = [page.evaluate("() => document.documentElement.dataset.motion"), css(page, "#stage .prism", "transitionDuration")]
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_function("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
        pick(page, "motion", "full")
        full = page.evaluate("() => document.documentElement.dataset.motion || null")
        pick(page, "motion", "auto")
        auto = page.evaluate("() => document.documentElement.dataset.motion || null")
        page.emulate_media(reduced_motion="no-preference")
        page.wait_for_function("() => !document.documentElement.dataset.motion", timeout=3000)   # the device's change followed
        auto2 = page.evaluate("() => document.documentElement.dataset.motion || null")
        check(red == ["reduce", "0s"] and full is None and auto == "reduce" and auto2 is None,
              "Réduites: the card turns at once; Normales whatever the device; Comme l'appareil follows it", [red, full, auto, auto2])

        # ---- compact list
        view(page, "words")
        h0 = page.evaluate("() => document.querySelector('#wlist .wrow').getBoundingClientRect().height")
        view(page, "display")
        page.click("#sw-compact")
        view(page, "words")
        h1 = page.evaluate("() => document.querySelector('#wlist .wrow').getBoundingClientRect().height")
        check(h1 < h0 * 0.8 and page.evaluate(OVERFLOW) <= 0, "compact list: lower rows", [h0, h1])
        shot(page, "aff-06-mots-compacte")
        view(page, "display")
        page.click('[data-look="textSize"] [data-v="l"]')
        page.set_viewport_size({"width": 375, "height": 667})
        view(page, "words")
        over = page.evaluate("""() => [...document.querySelectorAll('#wlist .wrow')].slice(0, 80).filter(r => r.querySelector('.p').getBoundingClientRect().right
            > r.querySelector('.r').getBoundingClientRect().left + 1).map(r => r.querySelector('.p').textContent)""")
        check(not over, "compact list, Grand, 375 px: no pinyin over the right column", over)
        page.set_viewport_size({"width": 390, "height": 844})
        view(page, "display")
        page.click('[data-look="textSize"] [data-v="m"]')
        view(page, "display")
        page.click("#sw-compact")

        # ---- the example switches, now here
        page.click("#sw-exform")
        exf = page.evaluate("() => [state.settings.exOnForm, !!prism.faces[0].querySelector('.form-ex'), document.querySelector('#sw-exform').getAttribute('aria-checked')]")
        page.click("#sw-exform")
        check(exf == [False, False, "false"] and page.evaluate("() => state.settings.exOnForm") is True, "the example's switch works from Affichage", exf)

        # ---- this device's own, the others shared; values left by another version
        doc = page.evaluate("() => Object.keys(docOf(state).settings)")
        check(not {"theme", "textSize", "motion", "compact", "zhFont"} & set(doc) and {"grid", "pinyinNum", "tonePalette", "toneColors"} <= set(doc),
              "synchronisation: theme, text size, motion, compact list and font stay on the device; the rest is shared", sorted(doc))
        merged = page.evaluate("""() => { const l = docOf(state), b = JSON.parse(JSON.stringify(l));
            for (const k of ['grid', 'pinyinNum', 'tonePalette']) delete b.settings[k];        // a base written before these settings
            const r = JSON.parse(JSON.stringify(b)); Object.assign(r.settings, { grid: 'mi', pinyinNum: true, tonePalette: 'pleco' });
            const m = mergeDocs(b, l, r).settings; return [m.grid, m.pinyinNum, m.tonePalette]; }""")
        check(merged == ["mi", True, "pleco"], "the first merge after the update: the other device's choices kept, not this one's defaults", merged)
        other = page.evaluate("""() => { const s = JSON.parse(localStorage.getItem('xingyinyi.v2')); s.settings.pinyinNum = true; s.settings.grid = 'mi';
            reloadState(JSON.stringify(s));
            return [document.querySelector('#sw-pynum').getAttribute('aria-checked'), document.querySelector('[data-look="grid"] [data-v="mi"]').getAttribute('aria-checked'),
                    document.querySelector('#look-sample .py').textContent, prism.faces[1].querySelector('.py').textContent]; }""")
        page.evaluate("""() => { const s = JSON.parse(localStorage.getItem('xingyinyi.v2')); s.settings.pinyinNum = false; s.settings.grid = 'tian'; reloadState(JSON.stringify(s)); }""")
        check(other[:3] == ["true", "true", "ni3 hao3"] and any(c.isdigit() for c in other[3]),
              "set in another window: Affichage and the card follow at once", other)
        bad = page.evaluate("""() => { const s = normalizeState({ v: 2, settings: { theme: 'rose', textSize: 'huge', zhFont: 3, grid: null,
            tonePalette: 'x', motion: 'z', pinyinNum: 'oui', compact: 0 } }).settings;
            return [s.theme, s.textSize, s.zhFont, s.grid, s.tonePalette, s.motion, s.pinyinNum, s.compact]; }""")
        check(bad == ["auto", "m", "kai", "tian", "app", "auto", True, False], "unknown values: the defaults", bad)
        page.click('#themes [data-v="auto"]')
        ctx.close()

        # ------------------------------------------------------------ the computer
        print("== ordinateur")
        ctx, page = new_page(browser, errors, size=(1366, 768), mobile=False)
        page.goto(url)
        wait_ready(page)
        view(page, "display")
        lay = page.evaluate("""() => { const t = [...document.querySelectorAll('.tab')].map(x => x.getBoundingClientRect());
            return { column: t.every((b, i) => !i || b.top > t[i - 1].top), lefts: new Set([...document.querySelectorAll('#view-display .sgroup')].map(x => Math.round(x.getBoundingClientRect().left))).size }; }""")
        check(lay["column"] and lay["lefts"] >= 2, "computer: Affichage in the menu, its groups in columns", lay)
        shot(page, "aff-07-ordinateur")
        page.focus('#themes [data-v="sepia"]')
        page.keyboard.press("Enter")
        focus = page.evaluate("() => [document.activeElement.dataset.v, document.documentElement.dataset.theme]")
        check(focus == ["sepia", "sepia"], "a theme chosen with the keyboard: the focus stays on it", focus)
        names = page.evaluate("() => [...document.querySelectorAll('#themes .theme')].map(b => b.querySelector('.swatch').getAttribute('aria-hidden'))")
        check(set(names) == {"true"}, "the swatches are not read aloud (the theme's name only)", names)
        page.click('#themes [data-v="paper"]')
        shot(page, "aff-08-ordinateur-papier")
        view(page, "study")
        page.click("#turnbtn")
        page.wait_for_timeout(650)
        shot(page, "aff-09-ordinateur-carte-papier")
        view(page, "display")
        page.click('#themes [data-v="night"]')
        pick(page, "textSize", "l")
        view(page, "study")
        check(page.evaluate(OVERFLOW) <= 0, "computer, Grand: the review fits", page.evaluate(OVERFLOW))
        shot(page, "aff-10-ordinateur-nuit-grand")
        ctx.close()

        browser.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
