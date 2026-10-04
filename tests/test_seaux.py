# -*- coding: utf-8 -*-
"""Seaux et file d'attente, sur une petite liste (6 mots dans Perso, HSK 1 désactivée), en clair et en sombre :
premier tour complet, puis mots ratés repris à la fin de la file dans l'ordre où ils ont été ratés ; √ qui fait
monter d'un seau avec le délai de ce seau ; jours simulés (mots dus repris du plus ancien au plus récent, après le
premier tour ; le dernier seau reste le dernier) ; écrans de fin ; délais et nombre de seaux réglables (2 à 10) ;
entraînement libre sans effet sur le planning ; évaluation tirée dans tous les seaux (× au seau 0, √ sans effet),
arrêtée en cours de route ou menée au bout ; touches 1 et 2 ; compteurs de l'en-tête.
Lancer depuis la racine du dépôt :  py tests\\test_seaux.py
"""
import json
import os

from playwright.sync_api import sync_playwright

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, answer, nb

WORDS = [("图书馆", "túshūguǎn", "bibliothèque"), ("打印", "dǎyìn", "imprimer"), ("安排", "ānpái", "organiser"),
         ("复印", "fùyìn", "photocopier"), ("照片", "zhàopiàn", "photo"), ("电脑", "diànnǎo", "ordinateur")]
W = ["perso:" + h for h, _, _ in WORDS]
DELAYS = [1, 3, 7, 14, 30, 60]
DELAYS_OUT = ["1 j", "3 j", "1 sem.", "2 sem.", "1 mois", "2 mois"]

LINE = "() => [study.cur, ...study.queue].filter(Boolean)"
COUNTS = "() => [...document.querySelectorAll('#counts .count')].map(s => [+s.querySelector('b').textContent, s.lastChild.textContent])"
CHIPS = "() => [...document.querySelectorAll('#card-chip .chip')].map(c => c.textContent)"
CARDS = "(ids) => ids.map(id => state.cards[id] ? { ...state.cards[id], bucket: bucketOf(id), missed: missed(id), pass: inPass(id) } : null)"
HINTS = "() => [document.querySelector('#gi0').textContent, document.querySelector('#gi1').textContent]"
DONE = """() => ({ shown: !document.querySelector('#done').hidden, title: document.querySelector('#done-title').textContent,
  text: document.querySelector('#done-text').textContent, next: document.querySelector('#done-next').textContent,
  more: document.querySelector('#done-more').textContent,
  res: [...document.querySelectorAll('#done-more .evalres > span')].map(s => s.textContent),
  back: !document.querySelector('#done-back').hidden, evalBtn: !document.querySelector('#eval-start').hidden,
  freeBtn: !document.querySelector('#free-start').hidden })"""
PROGRESS = """() => ({ cols: document.querySelectorAll('#boxes .col').length,
  n: document.querySelector('#boxes').style.getPropertyValue('--n'),
  labels: [...document.querySelectorAll('#boxes-axis span')].map(s => s.firstChild.textContent),
  vals: [...document.querySelectorAll('#boxes-axis b')].map(b => +b.textContent),
  fc: [...document.querySelectorAll('#forecast-axis b')].map(b => +b.textContent),
  seen: document.querySelector('#seen-n').textContent, info: document.querySelector('#eval-info').textContent,
  evalOn: !document.querySelector('#eval-go').disabled, freeOn: !document.querySelector('#free-go').disabled })"""
SETTINGS = """() => ({ rows: document.querySelectorAll('#bucket-settings .set').length,
  steppers: document.querySelectorAll('#bucket-settings .stepper').length,
  outs: [...document.querySelectorAll('#bucket-settings output')].map(o => o.textContent),
  bk: [...document.querySelectorAll('#bucket-btns [data-bk]')].map(b => b.dataset.bk),
  ev: document.querySelector('#eval-val').textContent, top: topBucket(), delays: state.settings.delays,
  toast: document.querySelector('#toast').textContent })"""
# expected chips of the evaluation results, one per bucket met: "Seau 2" + "1/1"
PER_BUCKET = """() => {
  const per = {};
  for (const [ok, list] of [[1, study.res.ok], [0, study.res.ko]])
    for (const [, b] of list) { per[b] = per[b] || [0, 0]; per[b][0] += ok; per[b][1]++; }
  return Object.keys(per).map(Number).sort((x, y) => x - y).map(b => 'Seau ' + b + per[b][0] + '/' + per[b][1]);
}"""
# n days go by: every date of the planning moves n days back
AGE = """(n) => {
  for (const c of Object.values(state.cards)) {
    for (const k of ['d', 't', 's']) if (Number.isFinite(c[k])) c[k] -= n;
    if (c.k) c.k -= n * 864e5;
  }
  const log = {};
  for (const [d, v] of Object.entries(state.log)) log[+d - n] = v;
  state.log = log;
  save(); study.build();
}"""
# a few days later: W0 never seen, W3 missed three days ago, W1 due two days ago, W2 yesterday, W4 (last bucket) today,
# W5 not due before two days
SEED_DAYS = """(W) => {
  const T = dayNum();
  state.cards = {};
  state.cards[W[1]] = { b: 2, d: T - 2, t: T - 5, s: T - 9, r: 3, l: 0 };
  state.cards[W[2]] = { b: 3, d: T - 1, t: T - 8, s: T - 20, r: 4, l: 0 };
  state.cards[W[3]] = { b: 0, k: dayStart(T - 3) + 3600e3, f: T - 3, t: T - 3, s: T - 9, r: 3, l: 1 };
  state.cards[W[4]] = { b: 6, d: T, t: T - 60, s: T - 120, r: 8, l: 0 };
  state.cards[W[5]] = { b: 2, d: T + 2, t: T - 1, s: T - 9, r: 2, l: 0 };
  save(); study.build();
}"""
# every word met, spread over buckets 0 (missed), 1, 2, 3 and 6
SEED_EVAL = """(W) => {
  const T = dayNum();
  const at = [[0, { b: 0, k: Date.now() - 3600e3, f: T }], [1, { b: 1, d: T + 1 }], [2, { b: 2, d: T + 2 }],
              [3, { b: 3, d: T + 6 }], [4, { b: 6, d: T + 59 }], [5, { b: 6, d: T + 40 }]];
  state.cards = {};
  for (const [i, c] of at) state.cards[W[i]] = { r: 2, l: 0, t: T - 1, s: T - 10, ...c };
  save(); study.build();
}"""


def small_site(name):
    """Copie du site dont decks.json ne garde que Perso (6 mots) et HSK 1, désactivée."""
    site = fresh_copy(name)
    decks = os.path.join(site, "decks")
    cfg = {"listes": [{"id": "perso", "nom": "Perso", "fichier": "perso.tsv", "actif": True},
                      {"id": "hsk1", "nom": "HSK 1", "fichier": "hsk1.tsv", "actif": False}]}
    with open(os.path.join(decks, "decks.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    with open(os.path.join(decks, "perso.tsv"), "w", encoding="utf-8") as fh:
        fh.write("hanzi\tpinyin\tfrancais\n" + "".join("%s\t%s\t%s\n" % w for w in WORDS))
    return site


def plan(c):
    return (c["b"], c.get("d"), c.get("k"))


def run(browser, errors, scheme):
    print("== %s" % scheme)
    S = scheme + ": "
    site = small_site("site-seaux-" + scheme)
    httpd, url = serve(site)
    ctx, page = new_page(browser, errors, scheme)
    page.goto(url)
    wait_ready(page)
    T = page.evaluate("() => dayNum()")

    def line():
        return page.evaluate(LINE)

    def counts():
        return [[n, nb(t)] for n, t in page.evaluate(COUNTS)]

    def chips():
        return [nb(t) for t in page.evaluate(CHIPS)]

    def cards(ids=None):
        return page.evaluate(CARDS, ids or W)

    def hints():                                     # turns the card if needed, then reads the hints under × and √
        page.wait_for_function("() => study.ready && !!study.cur")
        if page.is_visible("#turnbtn"):
            page.click("#turnbtn")
        page.wait_for_selector("#grades:not([hidden])")
        return [nb(h) for h in page.evaluate(HINTS)]

    def done():
        page.wait_for_selector("#done:not([hidden])")
        return page.evaluate(DONE)

    def view(name):
        page.click('.tab[data-view="%s"]' % name)
        page.wait_for_timeout(300)

    # ------------------------------------------------------------ first pass
    st = page.evaluate("""() => ({ lists: LISTS.map(L => [L.id, L.words.length, deckOn(L.id)]), top: topBucket(),
        delays: state.settings.delays, evalSize: state.settings.evalSize, sched: state.sched,
        lineOf: lineOf(dayNum()), pass: DECK.filter(w => deckOn(w.deck)).every(w => inPass(w.id)) })""")
    check(line() == W and st["lineOf"] == W and st["pass"], S + "first pass: the six words of Perso, in file order", line())
    check(["hsk1", 150, False] in st["lists"], S + "inactive list left out of the line", st["lists"])
    check(st["top"] == 6 and st["delays"] == DELAYS and st["evalSize"] == 20 and st["sched"] == 1,
          S + "seven buckets by default (delays 1, 3, 7, 14, 30, 60 days)", st)
    check(counts() == [[6, "à voir"], [0, "à revoir"]], S + "header: 6 to see, 0 to review", counts())
    check(chips() == ["Nouveau mot", "Perso"], S + "chips of a word never seen", chips())
    r = page.evaluate("() => [study.startEval(), study.mode, document.querySelector('#toast').textContent]")
    check(r[0] is False and r[1] == "line" and "Rien à évaluer" in r[2], S + "no evaluation before any word is seen", r)
    h = hints()
    check(h == ["seau 0, fin de file", "seau 1, 1 jour"], S + "hints for a new word", h)

    a = answer(page, 1)
    c = cards([a])[0]
    check(a == W[0] and c["b"] == 1 and c["d"] == T + 1 and c["r"] == 1 and c["s"] == T and not c["pass"],
          S + "√ on a new word: bucket 1, back tomorrow", c)
    a = answer(page, 0)
    c = cards([a])[0]
    check(a == W[1] and c["b"] == 0 and c["missed"] and not c["pass"] and c["l"] == 0 and c["r"] == 1 and "d" not in c,
          S + "× on a new word: bucket 0, no lapse counted", c)
    check(line() == [W[2], W[3], W[4], W[5], W[1]], S + "the missed word goes to the end of the line", line())
    a2 = answer(page, 1, key=True)                    # key 2 = √
    a3 = answer(page, 1)
    a4 = answer(page, 0, key=True)                    # key 1 = ×
    c2, c4 = cards([a2, a4])
    check((a2, a3, a4) == (W[2], W[3], W[4]) and c2["b"] == 1 and c4["b"] == 0 and c4["missed"] and line() == [W[5], W[1], W[4]],
          S + "keys 2 and 1 answer √ and ×", (c2, c4, line()))
    answer(page, 1)
    check(line() == [W[1], W[4]], S + "first pass over: missed words come back, first missed first", line())
    check(counts() == [[0, "à voir"], [2, "à revoir"]], S + "header: 0 to see, 2 to review", counts())
    check(chips() == ["Seau 0, raté", "Perso"], S + "chip of a missed word", chips())
    h = hints()
    check(h == ["seau 0, fin de file", "seau 1, 1 jour"], S + "hints for a missed word", h)
    answer(page, 1)                                   # W1 √
    answer(page, 0)                                   # W4 × again: alone in the line, it comes straight back
    check(line() == [W[4]], S + "a word missed twice comes back again", line())
    answer(page, 1)
    d = done()
    lg = page.evaluate("() => state.log[dayNum()]") or {}
    check(d["title"] == "File terminée" and "3 révisions, 6 nouveaux mots" in nb(d["text"]), S + "done screen after the whole line", d)
    check(nb(d["next"]) == "Demain : 6 mots à revoir." and not d["back"] and d["evalBtn"] and d["freeBtn"], S + "done screen: tomorrow, buttons", d)
    check(lg.get("n") == 6 and lg.get("r") == 3 and lg.get("p") == 6, S + "day log: 6 new words, 3 reviews, 6 out of the first pass", lg)
    check(counts() == [[0, "à voir"], [0, "à revoir"]] and [c["b"] for c in cards()] == [1] * 6, S + "every word in bucket 1", cards())
    shot(page, "seaux-%s-01-done" % scheme)

    # ------------------------------------------------------------ Progress: the buckets
    view("progress")
    pr = page.evaluate(PROGRESS)
    check(pr["cols"] == 7 and pr["n"].strip() == "7" and [nb(x) for x in pr["labels"]] == ["ratés"] + DELAYS_OUT,
          S + "Progress: seven buckets, delays under them", pr["labels"])
    check(pr["vals"] == [0, 6, 0, 0, 0, 0, 0] and pr["seen"] == "6" and pr["fc"][:2] == [0, 6], S + "Progress: counts and forecast", pr)
    check(pr["evalOn"] and pr["freeOn"] and "prend 6 mots" in nb(pr["info"]), S + "Progress: evaluation of 6 words offered", pr["info"])
    page.click("#boxes .col >> nth=1")
    det = nb(page.inner_text("#boxes-detail"))
    check("Seau 1, de retour après 1 jour" in det, S + "bucket detail", det)
    page.locator("#boxes").scroll_into_view_if_needed()
    shot(page, "seaux-%s-02-progress" % scheme)

    # ------------------------------------------------------------ the next day
    view("study")
    page.evaluate(AGE, 1)
    check(line() == W and counts() == [[0, "à voir"], [6, "à revoir"]] and chips() == ["Seau 1", "Perso"],
          S + "next day: the six words are due, in order", (line(), counts(), chips()))
    h = hints()
    check(h == ["seau 0, fin de file", "seau 2, 3 jours"], S + "hints from bucket 1", h)
    a = answer(page, 1)
    c = cards([a])[0]
    check(a == W[0] and c["b"] == 2 and c["d"] == T + 3 and c["t"] == T, S + "√ from bucket 1: bucket 2, back in 3 days", c)
    a = answer(page, 0)
    c = cards([a])[0]
    check(a == W[1] and c["b"] == 0 and c["missed"] and c["l"] == 1 and line()[-1] == W[1], S + "× from bucket 1: bucket 0, a lapse, end of the line", c)

    # ------------------------------------------------------------ a few days later: order of the line, last bucket
    page.evaluate(SEED_DAYS, W)
    check(line() == [W[0], W[3], W[1], W[2], W[4]], S + "line: first pass first, then missed and due words, oldest first", line())
    check(counts() == [[1, "à voir"], [4, "à revoir"]], S + "header: 1 to see, 4 to review", counts())
    for _ in range(4):
        answer(page, 1)
    ch = chips()
    h = hints()
    check(ch == ["Seau 6", "Perso"] and h == ["seau 0, fin de file", "seau 6, 2 mois"], S + "last bucket: √ keeps the word there", (ch, h))
    answer(page, 1)
    cs = cards()
    check([c["b"] for c in cs] == [1, 3, 4, 1, 6, 2] and [c["d"] for c in cs] == [T + 1, T + 7, T + 14, T + 1, T + 60, T + 2],
          S + "each √ moves one bucket up, with that bucket's delay; bucket 6 stays at 6", [(c["b"], c["d"] - T) for c in cs])
    d = done()
    check(d["title"] == "File terminée" and nb(d["next"]) == "Demain : 2 mots à revoir.", S + "done screen: 2 words tomorrow", d)
    page.evaluate("() => { state.log = {}; save(); study.build(); }")
    d = done()
    check(d["title"] == "Rien à revoir pour l’instant" and counts() == [[0, "à voir"], [0, "à revoir"]], S + "nothing due: empty line screen", d)

    # ------------------------------------------------------------ Réglages: delays and number of buckets
    view("settings")
    se = page.evaluate(SETTINGS)
    check(se["rows"] == 7 and se["steppers"] == 6 and [nb(o) for o in se["outs"]] == DELAYS_OUT and se["bk"] == ["add", "remove"] and se["ev"] == "20",
          S + "Réglages: bucket 0 and six delays, add / remove", se)
    page.locator("#bucket-settings").scroll_into_view_if_needed()
    shot(page, "seaux-%s-03-settings" % scheme)
    page.click('#bucket-settings button[data-delay="1"][data-b="1"]')
    se = page.evaluate(SETTINGS)
    dd = [c["d"] for c in cards()]
    check(se["delays"] == [2, 3, 7, 14, 30, 60] and nb(se["outs"][0]) == "2 j" and "reset" in se["bk"]
          and dd == [T + 2, T + 7, T + 14, T + 2, T + 60, T + 2], S + "+ on bucket 1: 2 days, due dates of bucket 1 moved", (se["delays"], [x - T for x in dd]))
    page.click('#bucket-settings button[data-delay="-1"][data-b="1"]')
    se = page.evaluate(SETTINGS)
    check(se["delays"] == DELAYS and cards()[0]["d"] == T + 1 and "reset" not in se["bk"], S + "− on bucket 1: back to 1 day", se["delays"])
    page.click('#bucket-btns [data-bk="add"]')
    se = page.evaluate(SETTINGS)
    check(se["top"] == 7 and se["delays"] == DELAYS + [120] and se["steppers"] == 7, S + "a bucket added (delay 120 days)", se["delays"])
    view("progress")
    check(page.locator("#boxes .col").count() == 8, S + "Progress follows: eight buckets", page.locator("#boxes .col").count())
    view("settings")
    page.dispatch_event('#bucket-btns [data-bk="remove"]', "click")       # bucket 7 is empty: removed at once
    check(page.evaluate("() => state.settings.delays") == DELAYS, S + "an empty last bucket is removed without asking")
    page.dispatch_event('#bucket-btns [data-bk="remove"]', "click")       # bucket 6 holds W4: asks first
    conf = page.evaluate("""() => ({ sure: document.querySelectorAll('#bucket-btns .confirm [data-bk="remove"][data-sure]').length,
        cancel: document.querySelectorAll('#bucket-btns [data-bk="cancel"]').length, text: document.querySelector('#bucket-btns').textContent,
        n: state.settings.delays.length })""")
    check(conf["sure"] == 1 and conf["cancel"] == 1 and conf["n"] == 6 and "seau 5" in nb(conf["text"]),
          S + "removing a bucket that holds words asks first", conf)
    page.dispatch_event('#bucket-btns [data-bk="cancel"]', "click")
    se = page.evaluate(SETTINGS)
    check(se["delays"] == DELAYS and se["bk"] == ["add", "remove"] and cards()[4]["b"] == 6, S + "Annuler keeps the bucket", se)
    page.dispatch_event('#bucket-btns [data-bk="remove"]', "click")
    page.dispatch_event('#bucket-btns [data-bk="remove"][data-sure]', "click")
    se = page.evaluate(SETTINGS)
    c4 = cards()[4]
    check(se["delays"] == DELAYS[:5] and se["top"] == 5 and c4["b"] == 5 and c4["d"] == T + 30 and "Seau 6 retiré" in nb(se["toast"]),
          S + "last bucket removed: its words go down to bucket 5", (se["delays"], c4, se["toast"]))
    page.dispatch_event('#bucket-btns [data-bk="reset"]', "click")
    se = page.evaluate(SETTINGS)
    c4 = cards()[4]
    check(se["delays"] == DELAYS and se["bk"] == ["add", "remove"] and c4["b"] == 5 and c4["d"] == T + 30,
          S + "back to the 7 original buckets", (se["delays"], c4))
    for _ in range(12):
        if not page.locator('#bucket-btns [data-bk="add"]').count():
            break
        page.dispatch_event('#bucket-btns [data-bk="add"]', "click")
    se = page.evaluate(SETTINGS)
    check(se["top"] == 9 and se["steppers"] == 9 and "add" not in se["bk"], S + "ten buckets at most", se["delays"])
    page.dispatch_event('#bucket-btns [data-bk="reset"]', "click")
    for _ in range(20):                               # each bucket that still holds words asks for a confirmation
        if page.locator('#bucket-btns [data-bk="remove"][data-sure]').count():
            page.dispatch_event('#bucket-btns [data-bk="remove"][data-sure]', "click")
        elif page.locator('#bucket-btns [data-bk="remove"]').count():
            page.dispatch_event('#bucket-btns [data-bk="remove"]', "click")
        else:
            break
    se = page.evaluate(SETTINGS)
    check(se["top"] == 1 and se["steppers"] == 1 and "remove" not in se["bk"] and max(c["b"] for c in cards()) == 1,
          S + "two buckets at least, every word clamped to bucket 1", (se["delays"], [c["b"] for c in cards()]))
    page.dispatch_event('#bucket-btns [data-bk="reset"]', "click")
    check(page.evaluate("() => state.settings.delays") == DELAYS, S + "reset again")
    for _ in range(4):
        page.click("#eval-minus")
    v1 = page.inner_text("#eval-val")
    page.click("#eval-plus")
    v2 = page.inner_text("#eval-val")
    page.click("#eval-minus")
    check(v1 == "5" and v2 == "10" and page.evaluate("() => state.settings.evalSize") == 5, S + "evaluation size: 5 to 100 by 5", (v1, v2))

    # ------------------------------------------------------------ Entraînement libre: no change to the planning
    page.evaluate(SEED_EVAL, W)
    view("progress")
    before = page.evaluate("() => JSON.stringify([state.cards, state.log])")
    page.click("#free-go")
    page.wait_for_function("() => study.mode === 'free' && study.ready")
    check(sorted(line()) == sorted(W) and counts() == [[6, "en libre"]] and chips() == ["Entraînement libre", "Perso"] and page.is_visible("#free-note"),
          S + "free training over the words already seen", (line(), counts(), chips()))
    h = hints()
    check(h == ["à revoir", "su"], S + "free training hints", h)
    answer(page, 1)
    a = answer(page, 0)
    check(line()[-1] == a, S + "free training: a missed word comes back at the end", line())
    answer(page, 1, key=True)
    check(page.evaluate("() => JSON.stringify([state.cards, state.log])") == before, S + "free training leaves cards and log untouched")
    page.click("#free-stop")
    check(page.evaluate("() => study.mode") == "line" and not page.is_visible("#free-note"), S + "Arrêter goes back to the line")

    # ------------------------------------------------------------ Évaluation stopped after three words
    view("progress")
    check("prend 5 mots" in nb(page.inner_text("#eval-info")), S + "evaluation size shown in Progress", page.inner_text("#eval-info"))
    page.click("#eval-go")
    page.wait_for_function("() => study.mode === 'eval' && study.ready")
    ev = page.evaluate("() => { const ids = [study.cur, ...study.queue]; return { ids, b: ids.map(bucketOf), seen: ids.every(seen), test: !!document.querySelector('#card-chip .chip.test') }; }")
    check(len(ev["ids"]) == 5 and len(set(ev["ids"])) == 5 and sorted(ev["b"]) == [0, 1, 2, 3, 6] and ev["seen"],
          S + "evaluation: 5 words, every bucket represented", ev)
    ch = chips()
    check(ev["test"] and ch == ["Évaluation", "Seau %d" % ev["b"][0], "Perso"] and counts() == [[5, "à évaluer"]], S + "evaluation chips and header", (ch, counts()))
    h = hints()
    check(h == ["retour au seau 0", "rien ne change"] and nb(page.inner_text("#free-text")).startswith("Évaluation"), S + "evaluation hints and note", h)
    snap = dict(zip(W, cards()))
    a1 = answer(page, 1)
    a2 = answer(page, 0)
    a3 = answer(page, 1, key=True)
    now = dict(zip(W, cards()))
    check(plan(now[a1]) == plan(snap[a1]) and plan(now[a3]) == plan(snap[a3]) and now[a1]["r"] == snap[a1]["r"] + 1,
          S + "√ in an evaluation: planning untouched", (snap[a1], now[a1]))
    last = page.evaluate("() => { const L = lineOf(dayNum()); return L[L.length - 1]; }")
    check(now[a2]["b"] == 0 and now[a2]["missed"] and last == a2, S + "× in an evaluation: bucket 0, end of the line", (now[a2], last))
    page.wait_for_function("() => study.ready")
    page.click("#free-stop")
    d = done()
    want = page.evaluate(PER_BUCKET)
    h2 = page.evaluate("(id) => BYID.get(id).h", a2)
    check(d["title"] == "Évaluation terminée" and nb(d["text"]) == "2 sur 3 réussis (67 %)." and len(want) == 3 and d["res"] == want
          and h2 in d["more"] and d["back"], S + "Arrêter mid-evaluation shows the results so far", (d, want))
    shot(page, "seaux-%s-04-eval-stopped" % scheme)
    page.click("#done-back")
    check(page.evaluate("() => study.mode") == "line", S + "Reprendre la file after an evaluation")

    # ------------------------------------------------------------ Évaluation to the end
    page.evaluate(SEED_EVAL, W)
    view("progress")
    page.click("#eval-go")
    page.wait_for_function("() => study.mode === 'eval' && study.ready")
    snap = dict(zip(W, cards()))
    got = [(answer(page, g, key=k % 2 == 1), g) for k, g in enumerate([1, 0, 1, 1, 0])]
    d = done()
    want = page.evaluate(PER_BUCKET)
    now = dict(zip(W, cards()))
    ok = [i for i, g in got if g]
    ko = [i for i, g in got if not g]
    hz = page.evaluate("(ids) => ids.map(id => BYID.get(id).h)", ko)
    check(d["title"] == "Évaluation terminée" and nb(d["text"]) == "3 sur 5 réussis (60 %)." and d["res"] == want
          and [x[:6] for x in d["res"]] == ["Seau 0", "Seau 1", "Seau 2", "Seau 3", "Seau 6"], S + "evaluation over: score, one chip per bucket", (d, want))
    check(all(x in d["more"] for x in hz) and d["back"] and d["evalBtn"] and counts() == [], S + "evaluation over: missed words listed", d["more"])
    check(all(plan(now[i]) == plan(snap[i]) for i in ok) and all(now[i]["b"] == 0 and now[i]["missed"] for i in ko),
          S + "evaluation: √ untouched, × back to bucket 0", [(i, plan(now[i])) for i in W])
    tail = page.evaluate("() => lineOf(dayNum()).slice(-2)")
    check(tail == ko, S + "words missed in the evaluation wait at the end of the line, in order", (tail, ko))
    shot(page, "seaux-%s-05-eval-done" % scheme)
    page.click("#done-back")
    check(page.evaluate("() => study.mode") == "line" and line()[-2:] == ko, S + "back to the line after the evaluation", line())

    ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    check(ov == 0, S + "no horizontal overflow", ov)
    ctx.close()
    httpd.shutdown()


def main():
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for scheme in ("light", "dark"):
            run(browser, errors, scheme)
        browser.close()
    finish(errors)


if __name__ == "__main__":
    main()
