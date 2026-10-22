# -*- coding: utf-8 -*-
"""Mots › dessiner un caractère : reconnaissance sans ordre des traits (formes tirées de traits/), mesurée sur des
dessins faits des traits des caractères eux-mêmes, déformés, dans le désordre, à l'envers et parfois liés ; dessin au
doigt (téléphone) et à la souris (ordinateur) ; la proposition touchée s'ajoute à la recherche ; annuler un trait,
effacer ; hors ligne sans les formes ; mise en page.
Lancer depuis la racine du dépôt :  py tests\\test_dessin.py
"""
import json

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, nb

# The medians of every 7th character, drawn as a hand would (the same distortions as when the recognizer was tuned):
# each stroke moved and resized a little, the whole stretched, sheared and turned, the points wobbling; then the strokes
# shuffled, a third of them reversed, some joined to the one before. level 0: only the order, directions and joins.
QUALITY = """async (level) => {
  const S = await loadShapes(), meds = [];
  for (let n = 0; n < TPACKS; n++) { const d = await traitPack(n); for (const [ch, v] of Object.entries(d)) meds.push([ch, v[1].map(s => s.map(([x, y]) => [x, -y]))]); }
  let seed = 11;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }, rr = (a, b) => a + (b - a) * rnd();
  const draw = strokes => {
    const sx = rr(1 - .18 * level, 1 + .18 * level), sy = rr(1 - .18 * level, 1 + .18 * level), sh = rr(-.15, .15) * level, rot = rr(-.1, .1) * level;
    const cs = Math.cos(rot), sn = Math.sin(rot);
    let out = strokes.map(s => {
      const ox = rr(-35, 35) * level, oy = rr(-35, 35) * level, k = rr(1 - .15 * level, 1 + .15 * level);
      const mx = s.reduce((a, p) => a + p[0], 0) / s.length, my = s.reduce((a, p) => a + p[1], 0) / s.length, pts = [];
      for (let i = 1; i < s.length; i++) for (let t = 0; t < 1; t += .25) pts.push([s[i - 1][0] + (s[i][0] - s[i - 1][0]) * t, s[i - 1][1] + (s[i][1] - s[i - 1][1]) * t]);
      pts.push(s[s.length - 1]);
      return pts.map(([x, y]) => { x = mx + (x - mx) * k + ox + rr(-8, 8) * level; y = my + (y - my) * k + oy + rr(-8, 8) * level;
        x *= sx; y *= sy; x += sh * y; return [x * cs - y * sn, x * sn + y * cs]; });
    }).map(s => (rnd() < .35 ? s.slice().reverse() : s));
    for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
    const joined = [];
    for (const s of out) { if (joined.length && rnd() < .12) joined[joined.length - 1] = joined[joined.length - 1].concat(s); else joined.push(s); }
    return joined;
  };
  let n = 0, top1 = 0, top10 = 0;
  const t = performance.now();
  for (let i = 0; i < meds.length; i += 7) {
    const got = guessChars(S, draw(meds[i][1]));
    n++; if (got[0] === meds[i][0]) top1++; if (got.includes(meds[i][0])) top10++;
  }
  return { n, chars: S.packs.reduce((a, P) => a + P.chars.length, 0), top1: top1 / n, top10: top10 / n, ms: (performance.now() - t) / n };
}"""
CANDS = "() => [...document.querySelectorAll('#pad-cands [data-ch]')].map(b => b.dataset.ch)"
# the guess of the last stroke on screen (not that of a stroke before)
SETTLED = "() => pad.shown === pad.seq && document.querySelectorAll('#pad-cands [data-ch]').length === 10"
LINE = "() => [[[100, 500], [900, 500]]]"
MEDIANS = "async (ch) => (await strokesOf(ch))[1]"


def pad_points(page, medians, order=None, reverse=()):
    """The medians of a character as points on the pad (in the page), strokes in the given order, some reversed."""
    box = page.locator("#pad").bounding_box()
    order = order or list(range(len(medians)))
    out = []
    for i in order:
        pts = [(box["x"] + (x / 1024) * box["width"], box["y"] + ((900 - y) / 1024) * box["height"]) for x, y in medians[i]]
        out.append(pts[::-1] if i in reverse else pts)
    return out


def draw_mouse(page, strokes):
    for pts in strokes:
        page.mouse.move(*pts[0])
        page.mouse.down()
        for x, y in pts[1:]:
            page.mouse.move(x, y, steps=3)
        page.mouse.up()


def draw_finger(cdp, strokes):
    for pts in strokes:
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": pts[0][0], "y": pts[0][1]}]})
        for x, y in pts[1:]:
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def main():
    site = fresh_copy("site-dessin")
    httpd, url = serve(site)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ------------------------------------------------------------ the phone, with a finger
        print("== téléphone")
        ctx, page = new_page(browser, errors, offline_ok=True)   # it goes offline at the end
        cdp = ctx.new_cdp_session(page)
        page.goto(url)
        wait_ready(page)
        page.click('.tab[data-view="words"]')
        check(page.is_hidden("#drawpad") and page.get_attribute("#draw-open", "aria-expanded") == "false", "Mots: the pad closed at first")
        page.click("#draw-open")
        page.wait_for_selector("#drawpad:not([hidden])")
        hint = nb(page.inner_text("#pad-hint"))
        check("ordre de traits" in hint, "the pad open: a hint, no candidates yet", hint)

        q0 = page.evaluate(QUALITY, 0)
        q1 = page.evaluate(QUALITY, 1)
        check(q0["chars"] > 3000 and q0["top1"] >= 0.97, "strokes in any order and direction, some joined: the character first", q0)
        check(q1["top10"] >= 0.97 and q1["top1"] >= 0.85, "a sloppy drawing as well: among the ten proposed", q1)
        check(q1["ms"] < 20, "a few milliseconds per drawing", q1["ms"])

        page.fill("#q", "hao")
        med = page.evaluate(MEDIANS, "好")
        n = len(med)
        draw_finger(cdp, pad_points(page, med, order=list(range(n))[::-1], reverse={0, 2, 4}))
        page.wait_for_function(SETTLED)
        cands = page.evaluate(CANDS)
        check(cands[:3].count("好") == 1, "好 drawn with a finger, strokes backwards and in reverse order: proposed at once", cands)
        check(page.evaluate("() => pad.strokes.length") == n and page.evaluate("() => { const m = document.querySelector('#main'); return m.scrollWidth - m.clientWidth; }") <= 0,
              "each stroke kept; the pad within the phone's width")
        shot(page, "dessin-01-telephone")
        page.click('#pad-cands [data-ch="好"]')
        page.wait_for_function("() => document.querySelector('#q').value === '好'")
        rows = page.evaluate("""() => [...document.querySelectorAll('#wlist .wrow')].map(r => BYID.get(r.dataset.id))
            .map(w => [w.h, (w.h + (w.e || '')).includes('好')])""")   # the search also looks in the example sentences
        check(rows and any("好" in r[0] for r in rows) and all(r[1] for r in rows) and page.evaluate("() => pad.strokes.length") == 0
              and page.evaluate(CANDS) == [], "a candidate touched: the search « hao » becomes 好, its words listed, the pad clean for the next one", rows[:5])
        med = page.evaluate(MEDIANS, "人")
        draw_finger(cdp, pad_points(page, med))
        page.wait_for_function(SETTLED)
        check("人" in page.evaluate(CANDS)[:5], "a second character", page.evaluate(CANDS))
        page.click('#pad-cands [data-ch="人"]')
        check(page.input_value("#q") == "好人", "the second character after the first", page.input_value("#q"))
        # undo and clear
        med = page.evaluate(MEDIANS, "学")
        draw_finger(cdp, pad_points(page, med)[:3])
        page.click("#pad-undo")
        undo = page.evaluate("() => pad.strokes.length")
        page.click("#pad-clear")
        clear = page.evaluate("() => [pad.strokes.length, document.querySelectorAll('#pad-cands [data-ch]').length]")
        check(undo == 2 and clear == [0, 0], "Annuler le trait takes the last one off; Effacer, all", [undo, clear])
        # a second finger resting on the pad (the thumb holding the phone) is left out
        box = page.locator("#pad").bounding_box()
        x0, y0, tx, ty = box["x"] + 40, box["y"] + 60, box["x"] + box["width"] - 15, box["y"] + box["height"] - 15
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0, "id": 1}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y0, "id": 1}, {"x": tx, "y": ty, "id": 2}]})
        for k in range(1, 9):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + 18 * k, "y": y0, "id": 1}, {"x": tx, "y": ty, "id": 2}]})
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": tx, "y": ty, "id": 2}]})   # the first finger lifts
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        two = page.evaluate("() => pad.strokes.map(s => [s.length, Math.max(...s.map(p => p[1])) - Math.min(...s.map(p => p[1]))])")
        check(len(two) == 1 and two[0][0] >= 8 and two[0][1] < 0.02, "a second finger on the pad: left out, the first one's stroke straight", two)
        cancel = page.evaluate("""() => { const c = document.querySelector('#pad'), r = c.getBoundingClientRect(), before = pad.strokes.length;
            const o = { pointerId: 77, bubbles: true, isPrimary: true, clientX: r.left + 30, clientY: r.top + 30 };
            c.dispatchEvent(new PointerEvent('pointerdown', o)); c.dispatchEvent(new PointerEvent('pointermove', { ...o, clientX: r.left + 90 }));
            c.dispatchEvent(new PointerEvent('pointercancel', o)); return [before, pad.strokes.length, pad.id]; }""")
        check(cancel[1] == cancel[0] and cancel[2] is None, "a touch taken by the system (pointercancel): no stroke left", cancel)
        page.evaluate("() => { state.settings.theme = 'dark'; applyLook(state.settings); }")
        ink = page.evaluate("() => getComputedStyle(document.querySelector('#pad polyline')).stroke")
        page.evaluate("() => { state.settings.theme = 'auto'; applyLook(state.settings); }")
        check(ink == "rgb(227, 234, 225)", "the strokes in the theme's ink, changed with it (Tableau noir)", ink)
        page.click("#pad-clear")
        # the grid of Affichage on the pad too
        page.evaluate("() => { state.settings.grid = 'mi'; applyLook(state.settings); }")
        mi = page.evaluate("() => getComputedStyle(document.querySelector('.pad-box .mzg')).display")
        page.evaluate("() => { state.settings.grid = 'tian'; applyLook(state.settings); }")
        check(mi == "block", "the pad follows Affichage › Grille des cases (米字格)", mi)
        page.click("#draw-open")
        check(page.is_hidden("#drawpad"), "the pen button closes the pad")
        # offline before the shapes came: said so, the candidates of before cleared
        page.click("#draw-open")
        draw_finger(cdp, pad_points(page, page.evaluate(LINE)))
        page.wait_for_function(SETTLED)
        page.evaluate("async () => { await caches.delete('traits-xingyinyi'); traitPacks.clear(); shapePacks.clear(); shapes = null; }")
        ctx.set_offline(True)
        draw_finger(cdp, pad_points(page, page.evaluate("() => [[[512, 100], [512, 900]]]")))
        page.wait_for_function("() => pad.shown === pad.seq && /Hors ligne/.test(document.querySelector('#pad-hint').textContent)")
        check(page.evaluate(CANDS) == [], "offline without the shapes: said so, no candidates (those of before gone)", nb(page.inner_text("#pad-hint")))
        ctx.set_offline(False)
        # online, one packet that does not come: the others' candidates, said; asked again when the pad opens again
        page.route("**/traits/05.json", lambda route: route.abort())
        page.click("#draw-open")
        page.click("#draw-open")
        page.click("#pad-clear")
        draw_finger(cdp, pad_points(page, page.evaluate(MEDIANS, "好")))
        page.wait_for_function(SETTLED)
        part = [nb(page.inner_text("#pad-hint")), page.evaluate("() => shapesMissing"), "好" in page.evaluate(CANDS)[:3]]
        check("manque" in part[0] and part[1] == 1 and part[2], "one packet missing: the others' candidates, said", part)
        page.unroute("**/traits/05.json")
        ctx.close()

        # ------------------------------------------------------------ the computer, with the mouse
        print("== ordinateur")
        ctx, page = new_page(browser, errors, size=(1366, 768), mobile=False)
        page.goto(url)
        wait_ready(page)
        page.click('.tab[data-view="words"]')
        page.click("#draw-open")
        page.wait_for_selector("#drawpad:not([hidden])")
        side = page.evaluate("() => [document.querySelector('.pad-box').getBoundingClientRect().right, document.querySelector('.pad-side').getBoundingClientRect().left]")
        check(side[1] > side[0], "computer: the candidates beside the pad", side)
        med = page.evaluate(MEDIANS, "国")
        n = len(med)
        draw_mouse(page, pad_points(page, med, order=[2, 0, 4, 1, 3, 5, 6, 7][:n], reverse={1, 3}))
        page.wait_for_function(SETTLED)
        cands = page.evaluate(CANDS)
        check("国" in cands[:3], "国 drawn with the mouse in a wrong order: proposed", cands)
        shot(page, "dessin-02-ordinateur")
        page.focus('#pad-cands [data-ch="国"]')
        page.keyboard.press("Enter")
        kb = page.evaluate("() => [document.activeElement.id, document.querySelector('#q').value, document.querySelector('#pad-hint').textContent]")
        check(kb[0] == "pad" and kb[1] == "国" and "国" in kb[2], "a candidate chosen with the keyboard: the focus back on the pad, the choice said", kb)
        ctx.close()

        browser.close()
    httpd.shutdown()
    finish(errors)


if __name__ == "__main__":
    main()
