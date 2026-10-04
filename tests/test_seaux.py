# -*- coding: utf-8 -*-
"""Seaux et file d'attente, sur une petite liste (6 mots dans Perso, HSK 1 désactivée), en clair et en sombre :
premier tour complet, puis mots ratés repris à la fin de la file dans l'ordre où ils ont été ratés ; √ qui fait
monter d'un seau avec le délai de ce seau ; jours simulés (mots dus repris du plus ancien au plus récent, après le
premier tour ; le dernier seau reste le dernier) ; écrans de fin ; délais et nombre de seaux réglables (2 à 10) ;
entraînement libre sans effet sur le planning ; évaluation tirée dans tous les seaux (× au seau 0, √ sans effet),
arrêtée en cours de route ou menée au bout ; touches 1 et 2 ; compteurs de l'en-tête.
Test complet (Perso active, Extra et HSK 1 désactivées) : choix des listes, mots mélangés, effets de √ et × (un
nouveau mot réussi passe au seau 1), pause, reprise après rechargement, abandon, test mené au bout, sauvegarde
restaurée, liste modifiée ou désactivée pendant le test, cleanTest.
Sens connus (kn) : migration dans normalizeState, bit de la face de départ posé par √ (file, évaluation), effacé par
×, affichage (Mots, fiche du mot, étiquette sous la carte, Progrès).
Apprentissage : tirage dans le seau 0 des listes actives, taille réglable (5 à 50), boucle sans effet sur les cartes
(√ appris et au bout, × trois cartes plus loin), dernier passage noté comme la file, Arrêter, écrans de fin.
Test d'un nouveau sens : mots connus dans un ou deux sens, une question par sens manquant, face de départ imposée,
√ sans effet sur le planning, × au seau 0 sans aucun sens, autres questions du mot retirées, écran de fin par sens.
Lancer depuis la racine du dépôt :  py tests\\test_seaux.py
"""
import json
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from commun import check, serve, fresh_copy, new_page, wait_ready, shot, finish, answer, nb

WORDS = [("图书馆", "túshūguǎn", "bibliothèque"), ("打印", "dǎyìn", "imprimer"), ("安排", "ānpái", "organiser"),
         ("复印", "fùyìn", "photocopier"), ("照片", "zhàopiàn", "photo"), ("电脑", "diànnǎo", "ordinateur")]
W = ["perso:" + h for h, _, _ in WORDS]
DELAYS = [1, 3, 7, 14, 30, 60]
DELAYS_OUT = ["1 j", "3 j", "1 sem.", "2 sem.", "1 mois", "2 mois"]

LINE = "() => [study.cur, ...study.queue].filter(Boolean)"
COUNTS = "() => [...document.querySelectorAll('#counts .count')].map(s => [+s.querySelector('b').textContent, s.lastChild.textContent])"
CHIPS = "() => [...document.querySelectorAll('#card-chip .chip')].filter(c => !c.querySelector('.kn')).map(c => c.textContent)"
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

# ------------------------------------------------------------ full test
EXTRA = [("银行", "yínháng", "banque"), ("音乐", "yīnyuè", "musique"), ("帽子", "màozi", "chapeau"), ("香蕉", "xiāngjiāo", "banane")]
E = ["extra:" + h for h, _, _ in EXTRA]
HZ = dict(zip(W + E, [w[0] for w in WORDS + EXTRA]))
# answer given to each word of the full test (E3 leaves its list before it comes up): new words W0, W4, E0, E1, E2;
# bucket 3: W1, W3; missed: W2; bucket 6: W5
PLAN = {W[0]: 1, W[1]: 1, W[2]: 1, W[3]: 0, W[4]: 0, W[5]: 1, E[0]: 1, E[1]: 0, E[2]: 1}
SEED_TEST = """(W) => {
  const T = dayNum();
  state.cards = {};
  state.cards[W[1]] = { b: 3, d: T + 4, t: T - 3, s: T - 20, r: 4, l: 0 };
  state.cards[W[2]] = { b: 0, k: Date.now() - 3600e3, t: T, s: T - 9, r: 3, l: 1 };
  state.cards[W[3]] = { b: 3, d: T + 2, t: T - 5, s: T - 20, r: 5, l: 1 };
  state.cards[W[5]] = { b: 6, d: T + 40, t: T - 20, s: T - 120, r: 8, l: 0 };
  state.log = { [T]: { n: 2, r: 5, p: 2 }, [T - 1]: { n: 3, r: 1, p: 3 } };
  save(); study.build();
}"""
SAVED = "JSON.parse(localStorage.getItem('xingyinyi.v2'))"
TSTATE = """() => ({ test: state.test, saved: %s.test, mode: study.mode, cur: study.cur,
  line: [study.cur, ...study.queue].filter(Boolean), view: current, decks: JSON.stringify(state.decks),
  sheet: !document.querySelector('#sheet').hidden })""" % SAVED
SHEET = """() => ({ open: !document.querySelector('#sheet').hidden, title: document.querySelector('#sheet-title').textContent,
  rows: [...document.querySelectorAll('#sheet-body [data-tl]')].map(b => [b.dataset.tl, b.getAttribute('aria-checked'), b.closest('.set').textContent]),
  go: document.querySelector('#test-begin').textContent, off: document.querySelector('#test-begin').disabled,
  decks: JSON.stringify(state.decks), on: LISTS.map(L => [L.id, deckOn(L.id)]) })"""
TBTNS = "(sel) => [...document.querySelectorAll(sel + ' [data-test]')].map(b => [b.dataset.test, b.textContent])"
THEIGHTS = "(sel) => [...document.querySelectorAll(sel + ' [data-test]')].map(b => Math.round(b.getBoundingClientRect().height))"
CONFIRM = """(sel) => { const c = document.querySelector(sel + ' .confirm');
  return c && { text: c.querySelector('p').textContent, btns: [...c.querySelectorAll('[data-test]')].map(b => [b.dataset.test, b.textContent]) }; }"""
NOTE = """() => ({ shown: !document.querySelector('#free-note').hidden, text: document.querySelector('#free-text').textContent,
  stop: document.querySelector('#free-stop').textContent, chip: !!document.querySelector('#card-chip .chip.test') })"""
PRE = """() => ({ cur: study.cur, line: [study.cur, ...study.queue], q: state.test.queue, ok: state.test.ok, ko: state.test.ko,
  saved: %s.test, card: state.cards[study.cur] || null, pass: inPass(study.cur), missed: missed(study.cur),
  b: bucketOf(study.cur), now: Date.now() })""" % SAVED
POST = """(id) => ({ card: state.cards[id], pass: inPass(id), missed: missed(id), test: state.test, saved: %s.test,
  line: [study.cur, ...study.queue].filter(Boolean), lineOf: lineOf(dayNum()), log: JSON.stringify(state.log),
  now: Date.now(), T: dayNum(), mode: study.mode })""" % SAVED
TEST_RESUMED = "() => study.mode === 'test' && study.ready && !!study.cur"


def res_chips(records):
    """Chips expected under the results: "Nouveaux" (bucket -1) then one per bucket, "Seau 3" + "1/2"."""
    per = {}
    for _, g, b in records:
        per.setdefault(b, [0, 0])
        per[b][0] += g
        per[b][1] += 1
    return [("Nouveaux" if b < 0 else "Seau %d" % b) + "%d/%d" % tuple(per[b]) for b in sorted(per)]


def res_texts(records):
    """Score line and sentences expected on the end screen of a test."""
    ok, tot = sum(g for _, g, _ in records), len(records)
    score = "%d sur %d réussi%s (%d %%)." % (ok, tot, "s" if tot > 1 else "", int(100 * ok / tot + 0.5))
    up = sum(1 for _, g, b in records if g and b < 0)
    parts = []
    if up:
        parts.append("1 nouveau mot réussi passe directement au seau 1." if up == 1
                     else "%d nouveaux mots réussis passent directement au seau 1." % up)
    ko = [HZ[i] for i, g, _ in records if not g]
    parts.append("Ratés, au seau 0 : %s." % "、".join(ko) if ko else "Aucun mot raté.")
    return score, parts


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


def write_tsv(path, words):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("hanzi\tpinyin\tfrancais\n" + "".join("%s\t%s\t%s\n" % w for w in words))


def test_site(name):
    """Copie du site : Perso (6 mots, active), Extra (4 mots) et HSK 1, désactivées dans la file."""
    site = small_site(name)
    decks = os.path.join(site, "decks")
    cfg = {"listes": [{"id": "perso", "nom": "Perso", "fichier": "perso.tsv", "actif": True},
                      {"id": "extra", "nom": "Extra", "fichier": "extra.tsv", "actif": False},
                      {"id": "hsk1", "nom": "HSK 1", "fichier": "hsk1.tsv", "actif": False}]}
    with open(os.path.join(decks, "decks.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    write_tsv(os.path.join(decks, "extra.tsv"), EXTRA)
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


def run_test_mode(browser, errors, scheme):
    print("== %s, test complet" % scheme)
    S = scheme + ": test: "
    site = test_site("site-test-" + scheme)
    httpd, url = serve(site)
    ctx, page = new_page(browser, errors, scheme)
    page.goto(url)
    wait_ready(page)
    page.evaluate(SEED_TEST, W)
    log0 = page.evaluate("() => JSON.stringify(state.log)")
    records = []                                      # (id, grade, bucket before the answer, -1 for a new word)

    def counts():
        return [[n, nb(t)] for n, t in page.evaluate(COUNTS)]

    def chips():
        return [nb(t) for t in page.evaluate(CHIPS)]

    def hints():
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

    def tstate():
        return page.evaluate(TSTATE)

    def btns(sel):
        return [[k, nb(t)] for k, t in page.evaluate(TBTNS, sel)]

    def resume_btns(n):
        return [["resume", "Reprendre le test (%d mot%s)" % (n, "s" if n > 1 else "")], ["drop", "Abandonner le test"]]

    def begin(lists, label):
        """Taps Commencer le test. If the sheet does not start the test, says so, then starts it from the code so that
        the rest of the test mode is still checked."""
        page.click("#test-begin")
        try:
            page.wait_for_function(TEST_RESUMED, timeout=4000)
            started = True
        except PlaywrightTimeout:
            started = False
            page.evaluate("(ids) => { closeSheet(); showView('study'); study.startTest(ids); }", lists)
            page.wait_for_function(TEST_RESUMED)
        check(started, S + label + ": Commencer le test starts the test", page.evaluate(TSTATE))

    def play(n):
        """Answers the next n words of the test as PLAN says, checking each answer."""
        for _ in range(n):
            pre = page.evaluate(PRE)
            face = page.evaluate("() => study.curFace")
            cur, g = pre["cur"], PLAN[pre["cur"]]
            name = "Perso" if cur.startswith("perso:") else "Extra"
            what = "new word" if pre["pass"] else "missed word" if pre["missed"] else "word of bucket %d" % pre["b"]
            check(pre["q"][0] == cur and pre["line"] == pre["q"] and pre["saved"]["queue"] == pre["q"],
                  S + "%s on screen: still first in the saved test until answered" % cur, pre)
            want_chip = "Nouveau mot" if pre["pass"] else "Seau 0, raté" if pre["missed"] else "Seau %d" % pre["b"]
            ch, h, co = chips(), hints(), counts()
            check(ch == ["Test", want_chip, name] and co == [[len(pre["q"]), "à tester"]]
                  and h == ["retour au seau 0", "seau 1, 1 jour" if pre["pass"] else "rien ne change"],
                  S + "%s: chips, header count and hints of a %s" % (cur, what), (ch, co, h))
            a = answer(page, g, key=len(records) % 3 == 2)
            post = page.evaluate(POST, cur)
            records.append((cur, g, -1 if pre["pass"] else pre["b"]))
            left = pre["q"][1:]
            ok_p = [[i, b] for i, gg, b in records if gg]
            ko_p = [[i, b] for i, gg, b in records if not gg]
            if left:
                check(a == cur and post["test"]["queue"] == left and post["saved"]["queue"] == left and post["line"] == left
                      and post["test"]["ok"] == ok_p and post["test"]["ko"] == ko_p and post["saved"] == post["test"],
                      S + "%s answered: out of the queue, results saved in localStorage" % cur, (left, post["test"], post["saved"]))
            else:
                check(a == cur and post["test"] is None and post["saved"] is None, S + "last word answered: state.test back to null", post)
            check(post["log"] == log0, S + "%s: day log untouched" % cur, post["log"])
            c0, c, T = pre["card"] or {}, post["card"], post["T"]
            r0 = c0.get("r", 0)
            if pre["pass"] and g:
                check(c["b"] == 1 and c.get("d") == T + 1 and c["t"] == T and c["s"] == T and c["r"] == r0 + 1 and "k" not in c and not post["pass"]
                      and c["kn"] == 1 << face,
                      S + "√ on a new word (%s): bucket 1, back tomorrow" % cur, c)
            elif g:
                check(c == dict(c0, r=c0["r"] + 1, kn=c0.get("kn", 0) | 1 << face) and post["missed"] == pre["missed"],
                      S + "√ on a %s (%s): nothing changes but the review count and the way known" % (what, cur), (c0, c))
            else:
                lapse = 1 if c0.get("b", 0) >= 1 else 0
                last = post["lineOf"][-1] == cur if cur.startswith("perso:") else cur not in post["lineOf"]
                check(c["b"] == 0 and pre["now"] <= c.get("k", 0) <= post["now"] and "d" not in c and c["t"] == T
                      and c["l"] == c0.get("l", 0) + lapse and c["r"] == r0 + 1 and c["s"] == c0.get("s", T) and post["missed"] and last,
                      S + "× on a %s (%s): bucket 0, %s, end of the line" % (what, cur, "a lapse" if lapse else "no lapse"), (c0, c, post["lineOf"]))

    # ------------------------------------------------------------ Progress, then the sheet to choose the lists
    view("progress")
    info = nb(page.inner_text("#test-info"))
    check(btns("#test-box") == [["start", "Faire un test complet"]] and info.startswith("Tous les mots des listes que tu choisis"),
          S + "Progress offers a full test", (btns("#test-box"), info))
    decks0 = page.evaluate("() => JSON.stringify(state.decks)")
    page.click('#test-box [data-test="start"]')
    page.wait_for_selector("#test-begin")
    sh = page.evaluate(SHEET)
    check(sh["open"] and sh["title"] == "Test complet"
          and [[i, a, nb(t)] for i, a, t in sh["rows"]] == [["perso", "true", "Perso6 mots, dont 2 à voir"], ["extra", "false", "Extra4 mots, aucun encore vu, hors de la file"],
                                                           ["hsk1", "false", "HSK 1150 mots, aucun encore vu, hors de la file"]],
          S + "sheet: one switch per list, the lists active in the line ticked", sh["rows"])
    check(nb(sh["go"]) == "Commencer le test (6 mots)" and not sh["off"], S + "sheet: 6 words with Perso", sh["go"])
    gos = []
    for tl in ("extra", "hsk1", "hsk1", "perso", "extra"):
        page.click('#sheet-body [data-tl="%s"]' % tl)
        s = page.evaluate(SHEET)
        gos.append((nb(s["go"]), s["off"], s["decks"] == decks0))
    check([g[:2] for g in gos[:3]] == [("Commencer le test (10 mots)", False), ("Commencer le test (160 mots)", False), ("Commencer le test (10 mots)", False)],
          S + "sheet: ticking a list adds its words to the count", gos)
    check(gos[4][:2] == ("Choisis au moins une liste", True), S + "sheet: no list ticked, the button is disabled", gos[4])
    page.click('#sheet-body [data-tl="perso"]')
    page.click('#sheet-body [data-tl="extra"]')
    sh = page.evaluate(SHEET)
    check(all(g[2] for g in gos) and sh["decks"] == decks0 and ["extra", False] in sh["on"] and nb(sh["go"]) == "Commencer le test (10 mots)",
          S + "sheet: the switches leave the lists of the line alone", (sh["on"], sh["go"]))
    shot(page, "seaux-%s-06-test-sheet" % scheme)

    # ------------------------------------------------------------ the test starts, over Perso and Extra (off in the line)
    begin(["perso", "extra"], "first test")
    t = tstate()
    ts = t["test"]
    check(ts["lists"] == ["perso", "extra"] and ts["n"] == 10 and ts["ok"] == [] and ts["ko"] == [] and t["saved"] == ts
          and t["view"] == "study" and not t["sheet"] and t["mode"] == "test", S + "started over Perso and Extra, saved at once", t)
    check(sorted(ts["queue"]) == sorted(W + E) and len(set(ts["queue"])) == 10 and t["line"] == ts["queue"],
          S + "the words of the chosen lists, every one, even never seen", ts["queue"])
    check(ts["queue"] != W + E, S + "the words are shuffled", ts["queue"])
    check(t["decks"] == decks0 and not page.evaluate("() => deckOn('extra')") and counts() == [[10, "à tester"]],
          S + "Extra stays off in the line; header: 10 to test", (t["decks"], counts()))
    nt = page.evaluate(NOTE)
    check(nt["shown"] and nt["chip"] and nb(nt["stop"]) == "Pause"
          and nt["text"] == "Test : mot 1 sur 10",
          S + "note under the card, Pause button", nt)

    # a word leaves its list on the server while the test runs: it leaves the test, the rest carries on
    write_tsv(os.path.join(site, "decks", "extra.tsv"), EXTRA[:3])
    cur0 = t["cur"]
    page.wait_for_function("() => !checking")
    page.evaluate("() => refreshLists(false, false)")
    page.wait_for_function("(id) => !BYID.has(id) && study.ready", arg=E[3])
    t = tstate()
    want = [i for i in ts["queue"] if i != E[3]]
    check(t["mode"] == "test" and t["test"]["queue"] == want and t["saved"]["queue"] == want and t["line"] == want and t["test"]["n"] == 10
          and (cur0 == E[3] or t["cur"] == cur0) and counts() == [[9, "à tester"]],
          S + "a word removed from its list leaves the test, the others stay in order", (cur0, t))
    # a list of the test switched off in the line: the test keeps it
    view("settings")
    before = tstate()
    page.click('#deck-settings .switch[data-deck="perso"]')
    t = tstate()
    off = page.evaluate("() => deckOn('perso')")
    check(not off and t["mode"] == "test" and t["line"] == before["line"] and t["test"] == before["test"],
          S + "Perso switched off in the line: its words stay in the test", (off, t["line"]))
    page.click('#deck-settings .switch[data-deck="perso"]')
    check(page.evaluate("() => deckOn('perso')") and tstate()["line"] == before["line"], S + "Perso switched back on")
    view("study")
    shot(page, "seaux-%s-07-test-card" % scheme)

    # ------------------------------------------------------------ four answers, then a pause
    play(4)
    on_screen = page.evaluate("() => study.cur")
    page.click("#free-stop")
    d = done()
    score, parts = res_texts(records)
    t = tstate()
    check(d["title"] == "Test en pause" and nb(d["text"]) == score and d["res"] == res_chips(records) and all(p in nb(d["more"]) for p in parts),
          S + "Pause: partial results (score, one chip per bucket, missed words)", (d, score, res_chips(records), parts))
    check(nb(d["next"]) == "Encore 5 mots à tester. Tu peux reprendre le test plus tard, même après avoir fermé l’appli.",
          S + "Pause: 5 words still to test", d["next"])
    check(btns("#done-test") == resume_btns(5) and page.is_visible('#done-test [data-test="resume"]') and d["back"]
          and not page.evaluate("() => document.querySelector('#done-back').classList.contains('primary')"),
          S + "Pause: resume and drop buttons, resuming first", btns("#done-test"))
    check(min(page.evaluate(THEIGHTS, "#done-test")) >= 34, S + "test buttons: touch targets of 34 px at least", page.evaluate(THEIGHTS, "#done-test"))
    check(t["test"]["queue"][0] == on_screen and len(t["test"]["queue"]) == 5 and t["saved"] == t["test"] and counts() == [] and not page.is_visible("#free-note"),
          S + "Pause: the word on screen waits first in the saved test", t["test"])
    shot(page, "seaux-%s-08-test-paused" % scheme)

    # ------------------------------------------------------------ reload: the test is still there
    paused = t["test"]
    page.reload()
    wait_ready(page)
    t = tstate()
    check(t["test"] == paused and t["mode"] == "line", S + "after a reload: the test is still saved, the line comes back", t["test"])
    view("progress")
    info = nb(page.inner_text("#test-info"))
    nok = sum(g for _, g, _ in records)
    check(btns("#test-box") == resume_btns(5) and btns("#done-test") == resume_btns(5)
          and info.startswith("Test en cours (Perso, Extra) : 4 mots testés sur 10, dont %d réussi" % nok) and "Il reprend là où tu l’as laissé." in info,
          S + "after a reload: Progress offers to resume the test (5 words)", (btns("#test-box"), info))
    page.click('#test-box [data-test="resume"]')
    page.wait_for_function(TEST_RESUMED)
    t = tstate()
    check(t["line"] == paused["queue"] and t["cur"] == on_screen and t["view"] == "study" and counts() == [[5, "à tester"]],
          S + "Reprendre le test: the same five words, in the same order", t["line"])
    page.click("#free-stop")
    d = done()
    check(d["title"] == "Test en pause" and btns("#done-test") == resume_btns(5), S + "paused again at once: end screen offers to resume", d)
    page.click('#done-test [data-test="resume"]')
    page.wait_for_function(TEST_RESUMED)
    check(tstate()["line"] == paused["queue"], S + "resumed from the end screen", tstate()["line"])

    # ------------------------------------------------------------ two answers, Abandonner then Annuler in Progress
    play(2)
    view("progress")
    page.click('#test-box [data-test="drop"]')
    cf = page.evaluate(CONFIRM, "#test-box")
    check(cf and nb(cf["text"]) == "Abandonner le test ? Les mots déjà testés gardent leur nouveau seau ; les 3 mots restants ne seront pas testés."
          and " ?" in cf["text"] and [[k, nb(x)] for k, x in cf["btns"]] == [["drop-yes", "Abandonner le test"], ["cancel", "Garder le test"]],
          S + "Abandonner asks first, in the page", cf)
    page.click('#test-box [data-test="cancel"]')
    t = tstate()
    check(btns("#test-box") == resume_btns(3) and t["test"] and len(t["test"]["queue"]) == 3 and t["mode"] == "test",
          S + "Garder le test keeps the test", (btns("#test-box"), t["test"]))
    view("study")
    page.wait_for_function(TEST_RESUMED)

    # ------------------------------------------------------------ the last three words: Test terminé
    play(3)
    d = done()
    score, parts = res_texts(records)
    check(len(records) == 9 and sorted(i for i, _, _ in records) == sorted(W + E[:3]) and score == "6 sur 9 réussis (67 %)."
          and res_chips(records) == ["Nouveaux3/5", "Seau 01/1", "Seau 31/2", "Seau 61/1"], S + "the nine words were answered as planned", records)
    check(d["title"] == "Test terminé" and nb(d["text"]) == score and d["res"] == res_chips(records), S + "Test terminé: score, one chip per bucket and Nouveaux", d)
    check("3 nouveaux mots réussis passent directement au seau 1." in nb(d["more"]) and parts[-1] in nb(d["more"]),
          S + "Test terminé: new words gone to bucket 1, missed words listed", (d["more"], parts))
    t = tstate()
    check(t["test"] is None and t["saved"] is None and btns("#done-test") == [["start", "Faire un test complet"]] and d["back"]
          and page.evaluate("() => document.querySelector('#done-back').classList.contains('primary')") and counts() == [],
          S + "Test terminé: no test left, Faire un test complet again", (t["test"], btns("#done-test")))
    shot(page, "seaux-%s-09-test-done" % scheme)
    cs = dict(zip(W + E, page.evaluate(CARDS, W + E)))
    check([cs[i]["b"] for i in W + E[:3]] == [1, 3, 0, 0, 0, 6, 1, 0, 1] and cs[E[3]] is None and page.evaluate("() => JSON.stringify(state.log)") == log0,
          S + "buckets after the test; the removed word never got a card; log untouched", [(i, c and c["b"]) for i, c in cs.items()])
    view("progress")
    info = nb(page.inner_text("#test-info"))
    check(btns("#test-box") == [["start", "Faire un test complet"]] and info.startswith("Tous les mots des listes"), S + "Progress: Faire un test complet again", info)

    # ------------------------------------------------------------ a second test, paused then dropped from the end screen
    view("study")
    page.click('#done-test [data-test="start"]')
    page.wait_for_selector("#test-begin")
    sh = page.evaluate(SHEET)
    check([r[:2] for r in sh["rows"]] == [["perso", "true"], ["extra", "false"], ["hsk1", "false"]] and nb(sh["go"]) == "Commencer le test (6 mots)",
          S + "second test from the end screen: Perso ticked", sh)
    begin(["perso"], "second test")
    pre = page.evaluate(PRE)
    a = answer(page, 1)
    page.click("#free-stop")
    d = done()
    check(d["title"] == "Test en pause" and nb(d["next"]).startswith("Encore 5 mots à tester."), S + "second test paused after one word", d)
    page.click('#done-test [data-test="drop"]')
    cf = page.evaluate(CONFIRM, "#done-test")
    check(cf and nb(cf["text"]).endswith("les 5 mots restants ne seront pas testés."), S + "Abandonner on the end screen asks first", cf)
    page.click('#done-test [data-test="drop-yes"]')
    page.wait_for_function("() => state.test === null")
    t = tstate()
    c = page.evaluate("(id) => state.cards[id]", a)
    toast_txt = nb(page.inner_text("#toast"))
    check(t["test"] is None and t["saved"] is None and t["mode"] == "line" and toast_txt == "Test abandonné" and c["r"] == (pre["card"] or {}).get("r", 0) + 1,
          S + "test dropped: back to the line, the answer given stays", (t, toast_txt, c))
    view("progress")
    check(btns("#test-box") == [["start", "Faire un test complet"]], S + "test dropped: Progress offers a new one", btns("#test-box"))

    # ------------------------------------------------------------ a backup restored keeps the test in progress
    page.click('#test-box [data-test="start"]')
    page.wait_for_selector("#test-begin")
    begin(["perso"], "third test")
    answer(page, 0)
    backup = page.evaluate("() => backupText()")
    kept = tstate()["test"]
    page.click("#free-stop")
    done()
    page.click('#done-test [data-test="drop"]')
    page.click('#done-test [data-test="drop-yes"]')
    page.wait_for_function("() => state.test === null")
    view("settings")
    page.click("#bk-restore")
    page.fill("#rs-t", backup)
    page.click("#rs-go")
    page.wait_for_selector("#sheet", state="hidden")
    t = tstate()
    check(json.loads(backup)["state"]["test"] == kept and t["test"] == kept and t["saved"] == kept and t["mode"] == "line"
          and "Sauvegarde restaurée" in nb(page.inner_text("#toast")), S + "backup restored: the test in progress comes back", t["test"])
    view("progress")
    check(btns("#test-box") == resume_btns(5), S + "backup restored: Progress offers to resume (5 words)", btns("#test-box"))
    page.click('#test-box [data-test="resume"]')
    page.wait_for_function(TEST_RESUMED)
    check(tstate()["line"] == kept["queue"], S + "backup restored: the test resumes with its five words", tstate()["line"])
    r = page.evaluate("""() => { study.stop(); state.test.queue.splice(1, 0, 'perso:不在'); save();
        const ok = study.resumeTest(); return { ok, line: [study.cur, ...study.queue], q: state.test.queue }; }""")
    check(r["ok"] and r["line"] == kept["queue"] and r["q"] == kept["queue"], S + "resuming drops the words that no longer exist", r)
    r = page.evaluate("""() => { study.stop(); state.test.queue = ['perso:不在']; save();
        const ok = study.resumeTest(); return { ok, test: state.test, toast: document.querySelector('#toast').textContent }; }""")
    check(r["ok"] is False and r["test"] is None and "plus de mot" in r["toast"], S + "a test left without any word is closed", r)

    # ------------------------------------------------------------ the whole row of the sheet, one primary button
    view("progress")
    page.click('#test-box [data-test="start"]')
    page.wait_for_selector("#test-begin")
    page.click('.set.tl:has([data-tl="extra"]) .t')         # the list's name, not its switch
    sh = page.evaluate(SHEET)
    check([r[:2] for r in sh["rows"]] == [["perso", "true"], ["extra", "true"], ["hsk1", "false"]] and nb(sh["go"]) == "Commencer le test (9 mots)",
          S + "sheet: tapping a list's name ticks it", sh)
    begin(["perso", "extra"], "fourth test")
    page.wait_for_function("() => study.ready && !!study.cur")
    # Pause during the grade animation, then resume at once: the timer of the left session draws no card
    r = page.evaluate("""() => { prism.turn(1); const q = [...state.test.queue]; study.grade(1); study.stop(); study.resumeTest();
        return { q, cur: study.cur }; }""")
    page.wait_for_timeout(700)
    after = page.evaluate("() => ({ cur: study.cur, q: [...state.test.queue], ok: state.test.ok.length + state.test.ko.length })")
    check(r["cur"] == r["q"][1] and after["cur"] == r["q"][1] and after["q"] == r["q"][1:] and after["ok"] == 1,
          S + "Pause during the grade animation then resume: no word skipped", (r, after))
    # a word that changes id (phone word published into its twin list) keeps its place and its answers
    rn = page.evaluate("""() => { const q0 = [...state.test.queue], cur = study.cur, nxt = study.queue[0], done = state.test.ok[0][0];
        renameInStudy(nxt, 'perso:新'); const a = { q: [...state.test.queue], sq: [...study.queue] };
        renameInStudy(cur, 'perso:今'); const b = { q: [...state.test.queue], cur: study.cur };
        renameInStudy(done, 'perso:旧'); const c = state.test.ok[0][0];
        renameInStudy('perso:新', q0[q0.length - 1]);           // its twin is in the test already: no double
        return { q0, cur, nxt, a, b, c, d: [...state.test.queue], sq: [...study.queue] }; }""")
    q0, nxt = rn["q0"], rn["nxt"]
    check(rn["a"]["q"] == [("perso:新" if i == nxt else i) for i in q0] and rn["a"]["sq"][0] == "perso:新"
          and rn["b"]["cur"] == "perso:今" and rn["b"]["q"][0] == "perso:今" and rn["c"] == "perso:旧"
          and len(rn["d"]) == len(q0) - 1 and len(set(rn["d"])) == len(rn["d"]) and rn["sq"] == rn["d"][1:],
          S + "a word that changes id keeps its place and its answers in the test", rn)
    page.click("#free-stop")
    d = done()
    t = page.evaluate("() => ({ back: document.querySelector('#done-back').classList.contains('primary'), resume: !!document.querySelector('#done-test [data-test=resume].primary') })")
    check(not t["back"] and t["resume"], S + "paused test: one primary button on the end screen", t)
    view("progress")
    t = page.evaluate("() => ({ ev: document.querySelector('#eval-go').classList.contains('primary'), resume: !!document.querySelector('#test-box [data-test=resume].primary') })")
    check(not t["ev"] and t["resume"], S + "paused test: one primary button in Progress", t)
    # every word left has vanished: Reprendre closes the test and the buttons follow
    page.evaluate("() => { state.test.queue = ['perso:不在']; save(); renderProgress(); }")
    page.click('#test-box [data-test="resume"]')
    page.wait_for_function("() => state.test === null")
    check(btns("#test-box") == [["start", "Faire un test complet"]] and "plus de mot" in page.inner_text("#toast"),
          S + "a test with no word left: Reprendre closes it, the buttons follow", btns("#test-box"))

    # ------------------------------------------------------------ cleanTest and normalizeState
    cl = page.evaluate("""() => ({
        bad: [null, 'x', 3, [], {}, { queue: 'abc' }, { queue: [] }, { queue: [1, null, {}] }, { lists: ['perso'], queue: null }].map(cleanTest),
        fixed: cleanTest({ lists: 'perso', n: 'abc', queue: ['perso:打印', 5], ok: [['perso:安排', '3'], 'bad', [7, 1]],
                           ko: [['perso:复印', -5], ['perso:照片', 'x']] }),
        good: cleanTest({ lists: ['perso'], n: 6, queue: ['perso:打印'], ok: [['perso:安排', -1]], ko: [] }),
        noTest: normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3] }, cards: {} }).test,
        garbage: normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3] }, cards: {}, test: { queue: 'x' } }).test,
        kept: normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3] }, cards: {}, test: { lists: ['perso'], n: 2, queue: ['perso:打印'], ok: [], ko: [['perso:安排', 1]] } }).test,
        fresh: freshState().test })""")
    check(cl["bad"] == [None] * 9, S + "cleanTest rejects garbage and finished tests", cl["bad"])
    check(cl["fixed"] == {"lists": [], "n": 4, "queue": ["perso:打印"], "ok": [["perso:安排", 3]], "ko": [["perso:复印", -1], ["perso:照片", 0]]},
          S + "cleanTest keeps what is valid and repairs the rest", cl["fixed"])
    check(cl["good"] == {"lists": ["perso"], "n": 6, "queue": ["perso:打印"], "ok": [["perso:安排", -1]], "ko": []}, S + "cleanTest keeps a valid test as it is", cl["good"])
    check(cl["noTest"] is None and cl["garbage"] is None and cl["fresh"] is None
          and cl["kept"] == {"lists": ["perso"], "n": 2, "queue": ["perso:打印"], "ok": [], "ko": [["perso:安排", 1]]},
          S + "normalizeState: test kept when valid, null otherwise", cl)

    ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    check(ov == 0, S + "no horizontal overflow", ov)
    ctx.close()
    httpd.shutdown()


# ------------------------------------------------------------ ways known, learning round, new-way test
WAYS = ["le caractère", "le pinyin", "la traduction"]
FACES = "形音义"
KN_TEXT = {0: "Pas encore connu dans un sens.", 1: "Connu par le caractère.", 2: "Connu par le pinyin.",
           3: "Connu par le caractère et le pinyin.", 4: "Connu par la traduction.",
           5: "Connu par le caractère et la traduction.", 6: "Connu par le pinyin et la traduction.",
           7: "Connu dans les trois sens."}


def lit(kn):
    """Letters of 形音义 lit for a bitmask of ways known."""
    return "".join(FACES[f] for f in range(3) if kn & (1 << f))


KNCHIP = """() => { const k = document.querySelector('#card-chip .kn');
  return k && [...k.querySelectorAll('i.on')].map(i => i.textContent).join(''); }"""
KNCOUNTS = "() => [...document.querySelectorAll('#kn-counts .count')].map(s => [s.firstChild.textContent, +s.querySelector('b').textContent])"
KNROWS = """(ids) => ids.map(id => { const k = document.querySelector('.wrow[data-id="' + id + '"] .r .kn');
  return k && { lit: [...k.querySelectorAll('i.on')].map(i => i.textContent).join(''), all: [...k.querySelectorAll('i')].map(i => i.textContent).join(''),
                label: k.getAttribute('aria-label') }; })"""
# normalizeState: kn of the cards passed before the ways were kept, for each start face, and garbage values
MIGRATE_KN = """() => {
  const T = dayNum();
  const st = (f, cards) => normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3, 7, 14, 30, 60], startFace: f }, cards }).cards;
  const old = () => ({ a: { b: 2, d: T + 3, t: T - 1, s: T - 9, r: 3, l: 0 }, z: { b: 0, k: Date.now(), t: T, s: T - 9, r: 2, l: 1 },
                       top: { b: 6, d: T + 50, t: T - 10, s: T - 90, r: 9, l: 0 } });
  const faces = {};
  for (const f of [0, 1, 2, 'r']) { const c = st(f, old()); faces[f] = [c.a.kn, c.z.kn, c.top.kn]; }
  const g = st(1, { s1: { b: 1, kn: 'abc' }, s2: { b: 1, kn: 9 }, s3: { b: 2, kn: -1 }, s4: { b: 1, kn: 2.6 }, s5: { b: 3, kn: 5 },
                    s6: { b: 1, kn: 0 }, s7: { b: 1, kn: '6' }, s8: { b: 1, kn: null }, s9: { b: 2, kn: 1e9 }, s10: { b: 1, kn: 7 },
                    s11: { b: 2, kn: 'x', r: 2 }, s12: { b: 0, r: 1, l: 0 } });
  const kept = st(2, { a: { b: 2, d: T + 3, t: T - 1, s: T - 9, r: 3, l: 0, kn: 3 } }).a;
  return { faces, g: Object.fromEntries(Object.entries(g).map(([k, c]) => [k, c.kn])), kept };
}"""
# a state saved by the previous version (no kn), start face 2, written before a reload
OLD_STATE = """(W) => {
  const T = dayNum();
  const s = JSON.parse(localStorage.getItem('xingyinyi.v2'));
  s.settings.startFace = 2;
  s.cards = { [W[0]]: { b: 2, d: T + 3, t: T - 1, s: T - 9, r: 3, l: 0 },
              [W[1]]: { b: 0, k: dayStart(T) + 1000, t: T, s: T - 9, r: 2, l: 1 },
              [W[2]]: { b: 1, d: T + 1, t: T, s: T - 3, r: 1, l: 0, kn: 3 } };
  localStorage.setItem('xingyinyi.v2', JSON.stringify(s));
}"""
# Perso: W0 5 (形义), W1 0 (seen), W2 7, W3 2 (音), W4 never seen, W5 6 (音义); Extra (off): E0 7
SEED_KN = """([W, E]) => {
  const T = dayNum();
  state.cards = {};
  const kns = [5, 0, 7, 2, null, 6];
  W.forEach((id, i) => { if (kns[i] !== null) state.cards[id] = { b: i === 1 ? 1 : 2, d: T + 3, t: T - 1, s: T - 9, r: 2, l: 0, kn: kns[i] }; });
  state.cards[E[0]] = { b: 2, d: T + 3, t: T - 1, s: T - 9, r: 2, l: 0, kn: 7 };
  save(); study.build();
}"""
SHEETMETA = "() => document.querySelector('#sheet-body p.meta').textContent"


def run_knowledge(browser, errors, scheme):
    print("== %s, sens connus" % scheme)
    S = scheme + ": sens connus: "
    site = test_site("site-kn-" + scheme)
    httpd, url = serve(site)
    ctx, page = new_page(browser, errors, scheme)
    page.goto(url)
    wait_ready(page)
    T = page.evaluate("() => dayNum()")

    def view(name):
        page.click('.tab[data-view="%s"]' % name)
        page.wait_for_timeout(300)

    def card(i):
        return page.evaluate("(id) => state.cards[id] || null", i)

    def knchip():
        return page.evaluate(KNCHIP)

    # ------------------------------------------------------------ normalizeState
    mg = page.evaluate(MIGRATE_KN)
    check(mg["faces"] == {"0": [1, 0, 1], "1": [2, 0, 2], "2": [4, 0, 4], "r": [1, 0, 1]},
          S + "migration: a card passed before (seau >= 1, no kn) is known by the start face (形 when it is au hasard); "
          "bucket 0: none", mg["faces"])
    g = mg["g"]
    check(all(isinstance(v, int) and 0 <= v <= 7 for v in g.values()), S + "migration: every kn kept within 0..7", g)
    check(g["s1"] == 2 and g["s11"] == 2 and g["s4"] == 3 and g["s5"] == 5 and g["s6"] == 2 and g["s7"] == 6 and g["s10"] == 7
          and g["s8"] == 2 and g["s2"] == 1 and g["s3"] == 7 and g["s12"] == 0,
          S + "migration: numbers kept (within 0..7); garbage or 0 past bucket 0 -> the start face (an older version "
          "still open passed it); bucket 0: none", g)
    check(mg["kept"]["kn"] == 3, S + "migration: a kn already there is kept whatever the start face", mg["kept"])

    # through a reload: the state of the previous version (no kn), start face 2
    page.evaluate(OLD_STATE, W)
    page.reload()
    wait_ready(page)
    r = page.evaluate("(W) => ({ kn: W.slice(0, 3).map(id => state.cards[id].kn), f: state.settings.startFace })", W)
    check(r == {"kn": [4, 0, 3], "f": 2}, S + "reload of an old state: seau 2 without kn -> 义 (start face 2), missed -> 0, kn 3 kept", r)

    # ------------------------------------------------------------ the line: √ sets the bit of the start face
    page.evaluate("() => { state.cards = {}; state.log = {}; save(); study.build(); }")
    for f, w in (("0", W[0]), ("1", W[1]), ("2", W[2]), ("r", W[3])):
        page.click('#startface [data-face="%s"]' % f)
        page.wait_for_function("() => study.ready")
        face = page.evaluate("() => study.curFace")
        kc = knchip()
        a = answer(page, 1)
        c = card(a)
        check(a == w and (f == "r" or face == int(f)) and face in (0, 1, 2) and c["kn"] == 1 << face and c["b"] == 1 and kc is None,
              S + "line, start face %s: √ makes the word known by face %d (kn %d); no chip before" % (f, face, 1 << face), (a, face, c, kc))
    page.click('#startface [data-face="0"]')
    a = answer(page, 0)
    c = card(a)
    check(a == W[4] and c["kn"] == 0 and c["b"] == 0, S + "line: × on a new word, known in no way", c)
    a = answer(page, 1)
    check(a == W[5] and card(a)["kn"] == 1, S + "line: √ from 形", card(a))
    # W0 (形) and W1 (音义) due today: the bits add up, × clears them all
    page.evaluate("""(W) => { const T = dayNum();
        Object.assign(state.cards[W[0]], { b: 1, d: T, t: T - 1, kn: 1 });
        Object.assign(state.cards[W[1]], { b: 2, d: T, t: T - 1, kn: 6 });
        save(); study.build(); }""", W)
    page.wait_for_function("() => study.ready")
    cur, kc = page.evaluate("() => study.cur"), knchip()
    page.click('#startface [data-face="2"]')
    page.wait_for_function("() => study.ready")
    kc2 = knchip()
    a = answer(page, 1)
    c = card(a)
    check(cur == W[0] and kc == "形" and kc2 == "形" and c["kn"] == 5 and c["b"] == 2, S + "line: chip 形 under the card, √ from 义 adds 义 (kn 5)", (cur, kc, c))
    cur, kc = page.evaluate("() => study.cur"), knchip()
    c0 = card(cur)
    a = answer(page, 0)
    c = card(a)
    check(cur == W[1] and kc == "音义" and c["kn"] == 0 and c["b"] == 0 and c["l"] == c0["l"] + 1 and "d" not in c,
          S + "line: chip 音义, × forgets every way (kn 0), bucket 0, a lapse", (kc, c0, c))
    cur, kc = page.evaluate("() => study.cur"), knchip()
    check(cur == W[4] and kc is None, S + "line: no chip for a word known in no way", (cur, kc))

    # ------------------------------------------------------------ evaluation: √ adds the way, × clears
    view("progress")
    page.click("#eval-go")
    page.wait_for_function("() => study.mode === 'eval' && study.ready")
    for gr in (1, 0):
        pre = page.evaluate("() => ({ cur: study.cur, face: study.curFace, card: state.cards[study.cur] })")
        kc = knchip()
        a = answer(page, gr)
        c, c0 = card(a), pre["card"]
        if gr:
            check(c == dict(c0, r=c0["r"] + 1, kn=c0["kn"] | 1 << pre["face"]) and kc == (lit(c0["kn"]) or None),
                  S + "evaluation: √ adds the way of the start face, planning untouched", (c0, c, kc))
        else:
            check(c["kn"] == 0 and c["b"] == 0 and "d" not in c, S + "evaluation: × forgets every way", (c0, c))
    page.click("#free-stop")
    page.wait_for_selector("#done:not([hidden])")
    page.click("#done-back")
    page.wait_for_function("() => study.mode === 'line'")

    # ------------------------------------------------------------ display: Mots, word sheet, Progrès
    page.evaluate(SEED_KN, [W, E])
    view("words")
    rows = page.evaluate(KNROWS, W + [E[0]])
    want = [5, 0, 7, 2, 0, 6, 7]
    check(all(r and r["all"] == "形音义" for r in rows) and [r["lit"] for r in rows] == [lit(k) for k in want]
          and [r["label"] for r in rows] == [KN_TEXT[k] for k in want],
          S + "Mots: 形音义 on each row, the ways known lit, the sentence as its label", rows)
    shot(page, "seaux-%s-10-kn-words" % scheme)
    metas = []
    for i in W + [E[1]]:
        page.click('.wrow[data-id="%s"]' % i)
        page.wait_for_selector("#sheet:not([hidden])")
        metas.append(nb(page.evaluate(SHEETMETA)))
        page.click("#sheet .panel-head .close")
        page.wait_for_selector("#sheet", state="hidden")
    check(all(metas[i].endswith(" " + KN_TEXT[want[i]]) for i in (0, 1, 2, 3, 5)) and metas[1].startswith("Liste Perso. Seau 1,")
          and metas[4] == "Liste Perso. Pas encore vu." and metas[6] == "Liste Extra. Pas encore vu.",
          S + "word sheet: the ways known after the bucket, nothing for a word never seen", metas)
    view("progress")
    kn = [[nb(t), n] for t, n in page.evaluate(KNCOUNTS)]
    check(kn == [["Par le caractère", 2], ["Par le pinyin", 3], ["Par la traduction", 3], ["Les trois", 1]],
          S + "Progrès: words of the active lists known by each way, and in the three (Extra, off, left out)", kn)
    page.locator("#kn-counts").scroll_into_view_if_needed()
    shot(page, "seaux-%s-11-kn-progress" % scheme)

    ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    check(ov == 0, S + "no horizontal overflow", ov)
    ctx.close()
    httpd.shutdown()


# W1 in bucket 2 and W2 missed; W0, W3, W4, W5 never seen: the bucket 0 of Perso holds W0, W2, W3, W4, W5
SEED_LEARN = """(W) => {
  const T = dayNum();
  state.cards = {};
  state.cards[W[1]] = { b: 2, d: T + 3, t: T - 2, s: T - 9, r: 3, l: 0, kn: 1 };
  state.cards[W[2]] = { b: 0, k: Date.now() - 3600e3, t: T - 1, s: T - 9, r: 3, l: 1, kn: 0 };
  state.log = { [T]: { n: 1, r: 2, p: 1 } };
  save(); study.build();
}"""
LSTATE = """() => ({ mode: study.mode, cur: study.cur, line: [study.cur, ...study.queue].filter(Boolean),
  ids: study.learn ? [...study.learn.ids] : null, got: study.learn ? [...study.learn.got] : null, check: !!(study.learn && study.learn.check),
  snap: JSON.stringify([state.cards, state.log]), note: document.querySelector('#free-text').textContent,
  noteShown: !document.querySelector('#free-note').hidden, stop: document.querySelector('#free-stop').textContent,
  kn: !!document.querySelector('#card-chip .kn'), face: study.curFace, toast: document.querySelector('#toast').textContent,
  card: (study.cur && state.cards[study.cur]) || null, pass: study.cur ? inPass(study.cur) : null, missed: study.cur ? missed(study.cur) : null,
  now: Date.now(), pool: learnPool(), lineOf: lineOf(dayNum()) })"""
LPOST = """(id) => ({ card: state.cards[id] || null, missed: missed(id), log: state.log[dayNum()] || null, lineOf: lineOf(dayNum()),
  now: Date.now(), toast: document.querySelector('#toast').textContent })"""
# every word of the round learned but X, a learned word on screen; X leaves the lists (build(keep)): the last check
# starts at once, on another card
LEARN_VANISH = """() => {
  const L = study.learn, cur = study.cur, X = L.ids.find(id => id !== cur);
  for (const id of L.ids) if (id !== X) L.got.add(id);
  const w = BYID.get(X); BYID.delete(X);
  study.build(true);
  BYID.set(X, w);
  return { cur, X, check: L.check, now: study.cur, ready: study.ready, ids: [...L.ids], line: [study.cur, ...study.queue],
    chips: [...document.querySelectorAll('#card-chip .chip')].filter(c => !c.querySelector('.kn')).map(c => c.textContent),
    note: document.querySelector('#free-text').textContent, cards: JSON.stringify(state.cards) };
}"""
# a phone word that changes id (mergeTel) during a round keeps its place, and its "learned" mark
LEARN_RENAME = """() => {
  const L = study.learn, cur = study.cur, nxt = study.queue[0];
  L.got.add(nxt);
  renameInStudy(nxt, 'perso:新'); renameInStudy(cur, 'perso:今');
  return { had: [cur, nxt], cur: study.cur, q0: study.queue[0], n: study.queue.length, ids: [...L.ids], got: [...L.got] };
}"""
LINFO = """() => ({ go: document.querySelector('#learn-go').textContent, off: document.querySelector('#learn-go').disabled,
  info: document.querySelector('#learn-info').textContent })"""
LBTN = """() => ({ shown: !document.querySelector('#learn-start').hidden, text: document.querySelector('#learn-start').textContent,
  back: document.querySelector('#done-back').classList.contains('primary') })"""
# the primary buttons shown in a part of the page
PRIMARY = "(sel) => [...document.querySelectorAll(sel + ' .btn.primary')].filter(b => b.offsetParent !== null).map(b => b.textContent.trim())"


def run_learning(browser, errors, scheme):
    print("== %s, apprentissage" % scheme)
    S = scheme + ": apprentissage: "
    site = test_site("site-learn-" + scheme)
    httpd, url = serve(site)
    ctx, page = new_page(browser, errors, scheme)
    page.goto(url)
    wait_ready(page)
    page.evaluate(SEED_LEARN, W)
    T = page.evaluate("() => dayNum()")
    POOL = [W[0], W[2], W[3], W[4], W[5]]

    def counts():
        return [[n, nb(t)] for n, t in page.evaluate(COUNTS)]

    def chips():
        return [nb(t) for t in page.evaluate(CHIPS)]

    def hints():
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

    def ls():
        return page.evaluate(LSTATE)

    def linfo():
        li = page.evaluate(LINFO)
        return dict(li, go=nb(li["go"]), info=nb(li["info"]))

    def go_learn():
        view("progress")
        page.click("#learn-go")
        page.wait_for_function("() => study.mode === 'learn' && study.ready && !!study.cur")

    def stop_to_line():
        page.click("#free-stop")
        page.wait_for_function("() => study.mode === 'line' && (study.ready || !document.querySelector('#done').hidden)")

    def loop_step(g, label):
        """One answer in the loop: chips, hints, note before; then the place of the word in the loop, cards untouched."""
        pre = ls()
        cur, got, n = pre["cur"], set(pre["got"]), len(pre["ids"])
        want_chip = "Appris" if cur in got else "Seau 0, raté" if pre["missed"] else "Nouveau mot"
        ch, h, co = chips(), hints(), counts()
        check(ch == ["Apprentissage", want_chip, "Perso"] and not pre["kn"] and co == [[n - len(got), "à apprendre"]]
              and h == ["revient bientôt", "appris, revient plus tard"]
              and nb(pre["note"]) == "Apprentissage : %d sur %d mots appris" % (len(got), n) and nb(pre["stop"]) == "Arrêter",
              S + "%s: chips (%s), header, hints and note in the loop" % (label, want_chip), (ch, co, h, pre["note"]))
        a = answer(page, g)
        post = ls()
        rest = pre["line"][1:]
        if g:
            got.add(cur)
            rest.append(cur)
        else:
            got.discard(cur)
            rest.insert(min(3, len(rest)), cur)
        check(a == cur and post["snap"] == pre["snap"], S + "%s: the loop leaves cards and log untouched" % label)
        if len(got) == n:
            check(post["check"] and sorted(post["line"]) == sorted(pre["ids"]) and set(post["got"]) == got,
                  S + "%s: every word learned at once: the last check starts with the %d words" % (label, n), post)
        else:
            check(not post["check"] and post["line"] == rest and set(post["got"]) == got,
                  S + "%s: %s %s" % (label, "√: learned, back at the end of the loop" if g else "×: not learned, back 3 cards later",
                                     "(%d learned)" % len(got)), (pre["line"], post["line"], rest, sorted(post["got"])))
        return cur, want_chip

    # ------------------------------------------------------------ Progrès and the size of a round
    view("progress")
    li = linfo()
    check(li["go"] == "Apprendre 5 mots" and not li["off"] and li["info"].startswith("5 mots du seau 0 (jamais vus ou ratés), tirés au hasard")
          and page.evaluate("() => state.settings.learnSize") == 20,
          S + "Progrès: 5 words in bucket 0, fewer than the 20 of a round", li)
    pool = page.evaluate("() => learnPool()")
    check(sorted(pool) == sorted(POOL), S + "pool: never seen or missed words of the active lists, not bucket 2 nor Extra (off)", pool)
    view("settings")
    page.click('#deck-settings .switch[data-deck="hsk1"]')
    check(page.evaluate("() => deckOn('hsk1')"), S + "HSK 1 switched on")
    view("progress")
    li = linfo()
    check(li["go"] == "Apprendre 20 mots" and li["info"].startswith("20 mots du seau 0"), S + "Progrès: 20 words with HSK 1 on", li)
    snap0 = ls()["snap"]
    go_learn()
    st = ls()
    ids = st["ids"]
    check(len(ids) == 20 and len(set(ids)) == 20 and set(ids) <= set(st["pool"]) and W[1] not in ids
          and not any(i.startswith("extra:") for i in ids) and page.evaluate("(ids) => ids.map(bucketOf)", ids) == [0] * 20,
          S + "round of 20 words, all in bucket 0 of the active lists", ids)
    check(len(st["pool"]) == 155 and ids != st["pool"][:20] and st["line"] == ids and st["got"] == [] and not st["check"]
          and page.evaluate("() => current") == "study" and counts() == [[20, "à apprendre"]],
          S + "the 20 words are picked at random; header: 20 to learn", (len(st["pool"]), counts()))
    answer(page, 1)
    answer(page, 0)
    stop_to_line()
    st = ls()
    check(st["mode"] == "line" and st["snap"] == snap0 and not st["noteShown"] and st["line"] == st["lineOf"],
          S + "Arrêter in the loop: back to the line, nothing changed", st["mode"])

    view("settings")
    vals = [page.inner_text("#learn-val")]
    for _ in range(4):
        page.click("#learn-minus")
        vals.append(page.inner_text("#learn-val"))
    for _ in range(10):
        page.click("#learn-plus")
        vals.append(page.inner_text("#learn-val"))
    saved = page.evaluate("() => [state.settings.learnSize, JSON.parse(localStorage.getItem('xingyinyi.v2')).settings.learnSize]")
    check(vals == ["20", "15", "10", "5", "5"] + [str(5 * k) for k in range(2, 11)] + ["50"] and saved == [50, 50],
          S + "Réglages: words per round from 5 to 50 by 5, saved", (vals, saved))
    hs = page.evaluate("() => ['#learn-minus', '#learn-plus'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().height))")
    check(min(hs) >= 34, S + "Réglages: − and + of 34 px at least", hs)
    for _ in range(9):
        page.click("#learn-minus")
    check(page.inner_text("#learn-val") == "5" and page.evaluate("() => state.settings.learnSize") == 5, S + "Réglages: 5 words per round")
    ns = page.evaluate("""() => [3, 80, 'abc', 35].map(n => normalizeState({ v: 2, sched: 1, settings: { delays: [1, 3], learnSize: n }, cards: {} }).settings.learnSize)""")
    check(ns == [5, 50, 20, 35], S + "normalizeState: learnSize kept within 5..50, 20 by default", ns)
    view("progress")
    check(linfo()["go"] == "Apprendre 5 mots", S + "Progrès: 5 words per round", linfo())
    go_learn()
    st = ls()
    check(len(st["ids"]) == 5 and set(st["ids"]) <= set(st["pool"]) and counts() == [[5, "à apprendre"]], S + "round of 5 words (learnSize 5)", st["ids"])
    stop_to_line()
    view("settings")
    page.click('#deck-settings .switch[data-deck="hsk1"]')
    for _ in range(3):
        page.click("#learn-plus")
    check(not page.evaluate("() => deckOn('hsk1')") and page.evaluate("() => state.settings.learnSize") == 20, S + "HSK 1 off again, 20 words per round")

    # ------------------------------------------------------------ round 1: the loop
    view("study")
    page.click('#startface [data-face="r"]')
    snap0 = ls()["snap"]
    go_learn()
    st = ls()
    check(sorted(st["ids"]) == sorted(POOL) and st["line"] == st["ids"] and not st["check"] and st["noteShown"],
          S + "pool smaller than a round: every word of bucket 0 of the active lists", st["ids"])
    check(st["note"] == "Apprentissage : 0 sur 5 mots appris", S + "typography of the note (fine space before :, 5 mots bound)", st["note"])
    shot(page, "seaux-%s-12-learn-loop" % scheme)
    steps = []
    for k, g in enumerate([1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1]):
        steps.append(loop_step(g, "loop %d (%s)" % (k + 1, "√" if g else "×")))
    check(steps[6][1] == "Appris" and steps[6][0] == steps[0][0] and steps[1][0] == steps[5][0] == steps[9][0],
          S + "loop: a learned word comes back (Appris) and a × un-learns it; the check waits for all five learned at once",
          [s[1] for s in steps])
    st = ls()
    check(nb(st["toast"]) == "Les 5 mots sont appris : un dernier passage, et chaque mot réussi passe au seau 1.", S + "toast before the last check", st["toast"])
    check(st["toast"].startswith("Les 5 mots sont appris :"),
          S + "typography of the toast: number and noun bound by a no-break space (plural), fine space before :", repr(st["toast"][:30]))
    check(st["snap"] == snap0, S + "after the loop: cards and log as before the round")

    # ------------------------------------------------------------ round 1: the last check, graded like the line
    exp_log = dict(page.evaluate("() => state.log[dayNum()]"))
    ko, ok = [], []
    for i, g in enumerate([1, 1, 0, 1, 0]):
        pre = ls()
        cur, c0 = pre["cur"], pre["card"] or {}
        want_chip = "Seau 0, raté" if pre["missed"] else "Nouveau mot"
        ch, h, co = chips(), hints(), counts()
        check(ch == ["Dernier passage", want_chip, "Perso"] and co == [[5 - i, "à vérifier"]] and h == ["seau 0, fin de file", "seau 1, 1 jour"]
              and nb(pre["note"]) == "Dernier passage : mot %d sur 5" % (i + 1) and not pre["kn"] and pre["check"],
              S + "last check %d: chips, header, hints and note" % (i + 1), (ch, co, h, pre["note"]))
        if i == 0:
            shot(page, "seaux-%s-13-learn-check" % scheme)
        a = answer(page, g)
        post = page.evaluate(LPOST, cur)
        c = post["card"]
        exp_log["r" if c0.get("r") else "n"] += 1
        if pre["pass"]:
            exp_log["p"] += 1
        if g:
            want = {k: v for k, v in c0.items() if k != "k"}
            want.update(b=1, d=T + 1, t=T, r=c0.get("r", 0) + 1, l=c0.get("l", 0), s=c0.get("s", T), kn=c0.get("kn", 0) | 1 << pre["face"])
            check(a == cur and c == want and not post["missed"], S + "last check √ (%s): bucket 1, back tomorrow, known by face %d" % (cur, pre["face"]), (c0, c))
            ok.append(cur)
        else:
            check(a == cur and c["b"] == 0 and pre["now"] <= c["k"] <= post["now"] and "d" not in c and c["kn"] == 0 and c["l"] == c0.get("l", 0)
                  and c["r"] == c0.get("r", 0) + 1 and c["t"] == T and c["s"] == c0.get("s", T) and post["missed"] and post["lineOf"][-1] == cur,
                  S + "last check × (%s): bucket 0, missed, end of the line, no lapse" % cur, (c0, c))
            ko.append(cur)
        check(post["log"] == exp_log, S + "last check %d: day log counted like the line" % (i + 1), (post["log"], exp_log))
    d = done()
    more = nb(d["more"])
    check(d["title"] == "Apprentissage terminé" and nb(d["text"]) == "3 sur 5 réussis (60 %)." and d["res"] == []
          and "3 mots réussis passent au seau 1." in more and "Restent au seau 0, à la fin de la file : %s." % "、".join(HZ[i] for i in ko) in more,
          S + "Apprentissage terminé: score, words gone to bucket 1, words left in bucket 0", d)
    check(d["text"] == "3 sur 5 réussis (60 %)." and "Restent au seau 0, à la fin de la file :" in d["more"]
          and "3 mots réussis passent" in d["more"], S + "typography of the end screen", (d["text"], d["more"]))
    lb = page.evaluate(LBTN)
    check(d["back"] and lb["back"] and lb["shown"] and nb(lb["text"]) == "Apprendre 2 mots" and counts() == []
          and page.evaluate("() => lineOf(dayNum()).slice(-2)") == ko,
          S + "end screen: Reprendre la file, Apprendre 2 mots; the missed words wait at the end of the line", (lb, counts()))
    pb = page.evaluate(PRIMARY, "#done")
    hs = page.evaluate("() => ['#learn-start', '#done-back'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().height))")
    check(pb == ["Reprendre la file"] and min(hs) >= 34, S + "end screen: one primary button, touch targets of 34 px at least", (pb, hs))
    shot(page, "seaux-%s-14-learn-done" % scheme)

    # ------------------------------------------------------------ round 2: Arrêter in the loop, then in the check
    snap1 = ls()["snap"]
    page.click("#learn-start")
    page.wait_for_function("() => study.mode === 'learn' && study.ready && !!study.cur")
    st = ls()
    check(sorted(st["ids"]) == sorted(ko) and counts() == [[2, "à apprendre"]] and chips() == ["Apprentissage", "Seau 0, raté", "Perso"],
          S + "Apprendre 2 mots from the end screen: the two missed words", (st["ids"], counts(), chips()))
    first = answer(page, 1)
    st = ls()
    check(st["got"] == [first] and st["line"][-1] == first and counts() == [[1, "à apprendre"]], S + "round 2: one word learned", st["got"])
    stop_to_line()
    st = ls()
    check(st["mode"] == "line" and st["snap"] == snap1 and not st["noteShown"] and st["line"] == st["lineOf"],
          S + "Arrêter in the loop: back to the line, nothing changed", st["mode"])
    # the words of the round leave their list while it runs: the round ends, nothing changed
    go_learn()
    answer(page, 1)
    kept = page.evaluate("(ids) => ids.map(id => state.cards[id])", ko)
    tsv = os.path.join(site, "decks", "perso.tsv")
    was = os.stat(tsv).st_mtime
    write_tsv(tsv, [w for w in WORDS if "perso:" + w[0] not in ko])
    os.utime(tsv, (was + 5, was + 5))              # a later date, or the server may answer 304 within the same second
    page.wait_for_function("() => !checking")
    page.evaluate("() => refreshLists(false, false)")
    page.wait_for_function("(ids) => ids.every(id => !BYID.has(id))", arg=ko)
    d = done()
    check(d["title"] == "Apprentissage arrêté" and nb(d["text"]) == "Rien n’a changé dans tes seaux : un mot ne passe au seau 1 qu’au dernier passage."
          and d["more"] == "" and d["back"] and page.evaluate("(ids) => ids.map(id => state.cards[id])", ko) == kept,
          S + "the words of the round leave their list: Apprentissage arrêté, nothing changed", d)
    check(d["text"].startswith("Rien n’a changé dans tes seaux :"), S + "typography of Apprentissage arrêté (fine space before :)", repr(d["text"][:35]))
    was = os.stat(tsv).st_mtime
    write_tsv(tsv, WORDS)
    os.utime(tsv, (was + 5, was + 5))
    page.wait_for_function("() => !checking")
    page.evaluate("() => refreshLists(false, false)")
    page.wait_for_function("(ids) => ids.every(id => BYID.has(id))", arg=ko)
    if page.is_visible("#done-back"):                # the lists reloaded under an end screen go back to the line by themselves
        page.click("#done-back")
    page.wait_for_function("() => study.mode === 'line' && study.ready")
    check(page.evaluate("(ids) => ids.map(id => state.cards[id])", ko) == kept and ls()["snap"] == snap1,
          S + "the words back in their list, with their cards as they were", ls()["line"])
    go_learn()
    loop_step(1, "round 2, loop 1")
    loop_step(1, "round 2, loop 2")
    st = ls()
    check(st["check"] and nb(st["toast"]) == "Les 2 mots sont appris : un dernier passage, et chaque mot réussi passe au seau 1.",
          S + "round 2: last check", st["toast"])
    a = answer(page, 1)
    other = [i for i in ko if i != a][0]
    c_other = page.evaluate("(id) => state.cards[id]", other)
    page.click("#free-stop")
    d = done()
    more = nb(d["more"])
    check(d["title"] == "Apprentissage arrêté" and nb(d["text"]) == "1 sur 1 réussi (100 %)." and "1 mot réussi passe au seau 1." in more
          and "Aucun mot raté." in more and d["back"] and page.evaluate("(id) => state.cards[id].b", a) == 1,
          S + "Arrêter in the last check: partial results", d)
    check(c_other == json.loads(snap1)[0][other] and page.evaluate("(id) => missed(id)", other),
          S + "Arrêter in the last check: the word not checked stays as it was", c_other)
    page.click("#done-back")
    page.wait_for_function("() => study.mode === 'line'")

    # ------------------------------------------------------------ one word left: the check at once, Arrêter before any answer
    view("progress")
    li = linfo()
    check(li["go"] == "Apprendre 1 mot" and li["info"].startswith("1 mot du seau 0"), S + "Progrès: Apprendre 1 mot", li)
    check(not any(x in li["info"] for x in ("vus ou ratés", "tirés", "reviennent", "les aies tous")),
          S + "Progrès: the explanation agrees in the singular for 1 word", li["info"])
    snap2 = ls()["snap"]
    go_learn()
    answer(page, 1)
    st = ls()
    check(st["check"] and nb(st["toast"]) == "Le mot est appris : un dernier passage, et s’il est réussi, il passe au seau 1."
          and counts() == [[1, "à vérifier"]] and chips()[0] == "Dernier passage",
          S + "a single word learned: the last check at once", (st["toast"], counts()))
    stop_to_line()
    st = ls()
    check(st["mode"] == "line" and st["snap"] == snap2, S + "Arrêter in the last check before any answer: back to the line, nothing changed", st["mode"])

    # ------------------------------------------------------------ nothing left in bucket 0
    page.evaluate("""(id) => { const T = dayNum(); state.cards[id] = { ...state.cards[id], b: 1, d: T + 1, t: T }; delete state.cards[id].k;
        save(); study.build(); }""", other)
    view("progress")
    li = linfo()
    check(li["off"] and li["info"] == "Aucun mot au seau 0 dans les listes actives : tout a déjà été réussi au moins une fois.",
          S + "Progrès: no word in bucket 0, the button is disabled", li)
    r = page.evaluate("() => { const m = study.mode; return [study.startLearn(), m, study.mode, document.querySelector('#toast').textContent]; }")
    check(r[0] is False and r[1] == r[2] == "line" and nb(r[3]) == "Aucun mot au seau 0 dans les listes actives.",
          S + "startLearn with an empty pool: a toast, nothing starts", r)
    view("study")
    d = done()
    check(not page.evaluate(LBTN)["shown"], S + "end screen: no Apprendre button without words in bucket 0", d["title"])

    # ------------------------------------------------------------ the last word left to learn leaves the lists
    page.evaluate(SEED_LEARN, W)
    c0 = page.evaluate("() => state.cards")
    go_learn()
    v = page.evaluate(LEARN_VANISH)
    check(v["check"] and v["ready"] and len(v["ids"]) == 4 and v["X"] not in v["ids"] and v["now"] != v["cur"]
          and sorted(v["line"]) == sorted(v["ids"]) and v["chips"][0] == "Dernier passage" and nb(v["note"]) == "Dernier passage : mot 1 sur 4"
          and json.loads(v["cards"]) == c0,
          S + "the only word not learned leaves the lists: the last check starts at once, the loop card on screen dropped", v)
    got = [answer(page, 1) for _ in range(4)]
    d = done()
    cs = page.evaluate("(ids) => ids.map(id => state.cards[id])", v["ids"])
    check(sorted(got) == sorted(v["ids"]) and d["title"] == "Apprentissage terminé" and nb(d["text"]) == "4 sur 4 réussis (100 %)."
          and all(c["b"] == 1 and c["r"] == (c0.get(i) or {}).get("r", 0) + 1 for i, c in zip(v["ids"], cs)),
          S + "each word of the last check graded once: bucket 1, one review more", (got, d["title"], d["text"], cs))
    page.click("#done-back")
    page.wait_for_function("() => study.mode === 'line'")

    # ------------------------------------------------------------ a word that changes id during a round
    page.evaluate(SEED_LEARN, W)
    go_learn()
    rn = page.evaluate(LEARN_RENAME)
    cur, nxt = rn["had"]
    check(rn["cur"] == "perso:今" and rn["q0"] == "perso:新" and rn["n"] == 4 and "perso:今" in rn["ids"] and "perso:新" in rn["ids"]
          and cur not in rn["ids"] and nxt not in rn["ids"] and rn["got"] == ["perso:新"],
          S + "a word that changes id keeps its place in the round and its mark (renameInStudy)", rn)
    page.click("#free-stop")
    page.wait_for_function("() => study.mode === 'line'")

    page.evaluate(SEED_LEARN, W)
    go_learn()
    sl = page.evaluate(STOP_SLIDING)
    check(not sl["readyThen"] and sl["mode"] == "line" and sl["cur"] and sl["shown"] == sl["cur"] and sl["ready"],
          S + "Arrêter while the next card slides in: the card shown is the one of the line, ready to grade", sl)
    page.wait_for_function("() => study.mode === 'line' && study.ready")
    rl = page.evaluate("""() => { const cur = study.cur; renameInStudy(cur, 'perso:今'); const a = study.cur; renameInStudy('perso:今', cur);
        return [cur, a, study.cur]; }""")
    check(rl[1] == "perso:今" and rl[2] == rl[0], S + "the line: the word on screen follows its new id (renameInStudy)", rl)
    ld = page.evaluate("() => [1, 2, 3, 10, 20, 30].map(k => longDate(dayNum() + k))")
    check(all(" " not in d.split(",")[0].split(" ", 1)[1] for d in ld) and all("\xa0" in d for d in ld),
          S + "dates: the day and the month kept together by a no-break space", ld)

    ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
    check(ov == 0, S + "no horizontal overflow", ov)
    ctx.close()
    httpd.shutdown()


# Perso: W0 形 (bucket 2), W1 形音 (1), W2 all three, W3 音 (1, a lapse), W4 none (1), W5 音义 (2); Extra (off): E0 形
SEED_SENS = """([W, E]) => {
  const T = dayNum();
  state.cards = {};
  const c = (b, kn, more) => ({ b, d: T + 5, t: T - 2, s: T - 20, r: 3, l: 0, kn, ...more });
  state.cards[W[0]] = c(2, 1);
  state.cards[W[1]] = c(1, 3);
  state.cards[W[2]] = c(3, 7);
  state.cards[W[3]] = c(1, 2, { l: 1 });
  state.cards[W[4]] = c(1, 0);
  state.cards[W[5]] = c(2, 6);
  state.cards[E[0]] = c(2, 1);
  state.log = { [T]: { n: 1, r: 4, p: 1 } };
  save(); study.build();
}"""
STARTFACE = """() => ({ locked: document.querySelector('#startface').getAttribute('aria-disabled'),
  checked: [...document.querySelectorAll('#startface [aria-checked="true"]')].map(b => b.dataset.face) })"""
DONEBTNS = """() => ({ learn: !document.querySelector('#learn-start').hidden, eval: !document.querySelector('#eval-start').hidden,
  free: !document.querySelector('#free-start').hidden })"""
# Arrêter while the next card slides in (170 ms): the card of the left session is not drawn over the new one
STOP_SLIDING = """async () => {
  prism.turn(1);
  study.grade(1);
  await new Promise(r => { const t = setInterval(() => { if (!study.busy) { clearInterval(t); r(); } }, 5); });
  const sliding = study.cur, readyThen = study.ready;
  study.stop();
  await new Promise(r => setTimeout(r, 400));
  return { sliding, readyThen, mode: study.mode, cur: study.cur, shown: prism.word && prism.word.id, ready: study.ready };
}"""
STATUS_LINES = "() => { const c = [...document.querySelectorAll('#card-chip .chip')]; return new Set(c.map(x => x.offsetTop)).size; }"
SSTATE = """() => ({ mode: study.mode, cur: study.cur, face: study.curFace, start: prism.start,
  shown: [...document.querySelectorAll('#stage .face')].findIndex(f => f.getAttribute('aria-hidden') === 'false'),
  items: study.cur ? [[study.cur, study.curFace], ...study.queue.map(x => [x.id, x.face])] : [],
  card: (study.cur && state.cards[study.cur]) || null, note: document.querySelector('#free-text').textContent,
  stop: document.querySelector('#free-stop').textContent, setting: state.settings.startFace,
  log: JSON.stringify(state.log), snap: JSON.stringify(state.cards), now: Date.now() })"""
SPOST = """(id) => ({ card: state.cards[id], missed: missed(id), log: JSON.stringify(state.log), now: Date.now(),
  items: study.cur ? [[study.cur, study.curFace], ...study.queue.map(x => [x.id, x.face])] : [] })"""
# sensPick drawn many times: the items each time, and how often one word comes twice in a row
SENS_DRAWS = """(want) => {
  const key = it => JSON.stringify(it.map(x => [x.id, x.face]).sort());
  const goal = JSON.stringify(want.slice().sort());
  let adj = 0, wrong = 0, ex = null; const orders = new Set();
  for (let i = 0; i < 300; i++) {
    const it = sensPick(20);
    orders.add(it.map(x => x.id + x.face).join());
    if (key(it) !== goal) wrong++;
    if (it.some((x, k) => k && x.id === it[k - 1].id)) { adj++; ex = ex || it.map(x => [x.id, x.face]); }
  }
  const two = sensPick(2).map(x => [x.id, x.face]);
  return { adj, wrong, ex, orders: orders.size, two };
}"""


def run_sens(browser, errors, scheme):
    print("== %s, nouveau sens" % scheme)
    S = scheme + ": nouveau sens: "
    site = test_site("site-sens-" + scheme)
    httpd, url = serve(site)
    ctx, page = new_page(browser, errors, scheme)
    page.goto(url)
    wait_ready(page)
    page.evaluate(SEED_SENS, [W, E])
    T = page.evaluate("() => dayNum()")
    ITEMS = [[W[0], 1], [W[0], 2], [W[1], 2], [W[3], 0], [W[3], 2], [W[5], 0]]
    MISSING = {W[0]: [1, 2], W[1]: [2], W[3]: [0, 2], W[5]: [0]}

    def counts():
        return [[n, nb(t)] for n, t in page.evaluate(COUNTS)]

    def chips():
        return [nb(t) for t in page.evaluate(CHIPS)]

    def hints():
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

    def ss():
        return page.evaluate(SSTATE)

    def kncounts():
        return [[nb(t), n] for t, n in page.evaluate(KNCOUNTS)]

    def go_sens():
        view("progress")
        page.click("#sens-go")
        page.wait_for_function("() => study.mode === 'sens' && study.ready && !!study.cur")

    # ------------------------------------------------------------ the pick
    view("progress")
    info = nb(page.inner_text("#sens-info"))
    check(kncounts() == [["Par le caractère", 3], ["Par le pinyin", 4], ["Par la traduction", 2], ["Les trois", 1]]
          and not page.evaluate("() => document.querySelector('#sens-go').disabled")
          and info.startswith("Le test prend au hasard jusqu’à 4 mots connus dans un ou deux sens"),
          S + "Progrès: ways known, Tester un nouveau sens offered for 4 words", (kncounts(), info))
    pb = page.evaluate(PRIMARY, "#view-progress")
    hs = page.evaluate("() => ['#learn-go', '#sens-go'].map(s => Math.round(document.querySelector(s).getBoundingClientRect().height))")
    check(pb == ["Faire une évaluation"] and min(hs) >= 34, S + "Progrès: one primary button; Apprendre and Tester of 34 px at least", (pb, hs))
    sub = page.evaluate("() => document.querySelector('#kn-counts').previousElementSibling.textContent")
    check(" :" in sub and " :" not in sub, S + "typography of the Sens connus explanation (fine space before :)", sub)
    dr = page.evaluate(SENS_DRAWS, ITEMS)
    check(sorted(page.evaluate("() => sensPool()")) == sorted(MISSING) and dr["wrong"] == 0,
          S + "sensPick: the words of the active lists known in one or two ways, one item per way missing", dr)
    check(dr["orders"] > 10, S + "sensPick: the items are shuffled", dr["orders"])
    two = dr["two"]
    tw = {}
    for i, f in two:
        tw.setdefault(i, []).append(f)
    check(len(tw) == 2 and all(sorted(fs) == MISSING[i] for i, fs in tw.items()), S + "sensPick(2): two words, each with all its missing ways", two)
    check(dr["adj"] == 0, S + "sensPick: never the same word twice in a row when it can be avoided (%d draws out of 300 had it)" % dr["adj"], dr["ex"])

    # ------------------------------------------------------------ the test
    go_sens()
    st = ss()
    check(sorted(st["items"]) == sorted(ITEMS) and counts() == [[6, "à tester"]] and page.evaluate("() => current") == "study",
          S + "started from Progrès: 6 items, header 6 to test", (st["items"], counts()))
    plan_g = {W[0]: [1, 0], W[1]: [1], W[3]: [0], W[5]: [1]}
    records = []                                       # (id, grade, face)
    while True:
        pre = ss()
        if not pre["cur"]:
            break
        cur, face, c0 = pre["cur"], pre["face"], pre["card"]
        g = plan_g[cur].pop(0)
        label = "%s par %s (%s)" % (HZ[cur], WAYS[face], "√" if g else "×")
        check([cur, face] in ITEMS and pre["start"] == face and pre["shown"] == face,
              S + "%s: the card starts on the face of the way tested" % label, pre)
        if not records:
            setting0 = pre["setting"]
            check(page.evaluate(STARTFACE) == {"locked": "true", "checked": [str(face)]},
                  S + "D’abord shows the face tested, locked", page.evaluate(STARTFACE))
            for f in [str((face + 1) % 3), "r"]:
                page.click('#startface [data-face="%s"]' % f, force=True)   # aria-disabled: a tap still reaches it
                p2, sf = ss(), page.evaluate(STARTFACE)
                toast = nb(page.evaluate("() => document.querySelector('#toast').textContent"))
                check(p2["face"] == face and p2["start"] == face and p2["shown"] == face and p2["setting"] == setting0
                      and sf == {"locked": "true", "checked": [str(face)]} and toast == "Pendant le test des sens, chaque carte part de la face à tester.",
                      S + "D’abord %s touched during the test: the setting stays, the card too, a toast" % f, (p2, sf, toast))
            shot(page, "seaux-%s-15-sens-card" % scheme)
        kc = page.evaluate(KNCHIP)
        ch, h, co = chips(), hints(), counts()
        check(ch == ["Par " + WAYS[face], "Perso"] and kc == lit(c0["kn"]) and co == [[len(pre["items"]), "à tester"]]
              and h == ["seau 0, plus aucun sens", "connu par " + WAYS[face]]
              and pre["note"] == "Nouveau sens : %d sur %d" % (len(records) + 1, len(records) + len(pre["items"]))
              and nb(pre["stop"]) == "Arrêter" and page.evaluate(STATUS_LINES) == 1,
              S + "%s: chips on one line, ways known under the card, header, hints, note (i sur answered + left)" % label,
              (ch, kc, co, h, pre["note"], page.evaluate(STATUS_LINES)))
        a = answer(page, g)
        post = page.evaluate(SPOST, cur)
        c = post["card"]
        records.append((cur, g, face))
        if g:
            check(a == cur and c == dict(c0, r=c0["r"] + 1, kn=c0["kn"] | 1 << face) and post["items"] == pre["items"][1:],
                  S + "%s: the way becomes known, bucket, due day and last review untouched" % label, (c0, c))
        else:
            lapse = 1 if c0["b"] >= 1 else 0
            check(a == cur and c["b"] == 0 and pre["now"] <= c["k"] <= post["now"] and "d" not in c and c["kn"] == 0 and c["l"] == c0["l"] + lapse
                  and c["r"] == c0["r"] + 1 and c["t"] == T and c["s"] == c0["s"] and post["missed"],
                  S + "%s: bucket 0, missed, a lapse, every way forgotten" % label, (c0, c))
            rest = [x for x in pre["items"][1:] if x[0] != cur]
            adj = [k for k in range(1, len(post["items"])) if post["items"][k][0] == post["items"][k - 1][0]]
            check(sorted(post["items"]) == sorted(rest) and (not adj or len({x[0] for x in rest}) == 1),
                  S + "%s: the other ways of the word leave the test; the same word never twice in a row if avoidable" % label,
                  (pre["items"], post["items"]))
        check(post["log"] == pre["log"], S + "%s: day log untouched" % label, post["log"])
    check(len(records) == 5 and all(not v for v in plan_g.values()), S + "five answers: the second way of 复印 left with its ×", records)
    d = done()
    lost = {i for i, g, _ in records if not g}         # every way of these words is lost, the ones gained in this test too
    per = {}
    for i, g, f in records:
        per.setdefault(f, [0, 0])
        per[f][0] += g and i not in lost
        per[f][1] += 1
    want_res = ["Par %s%d/%d" % (WAYS[f], per[f][0], per[f][1]) for f in sorted(per)]
    ko = [HZ[i] for i, g, _ in records if not g]
    more = nb(d["more"])
    check(any(i == W[0] and g for i, g, _ in records) and d["title"] == "Test des sens terminé" and nb(d["text"]) == "2 sur 5 réussis (40 %)."
          and [nb(x) for x in d["res"]] == want_res,
          S + "end screen: score, one chip per way; the way 图书馆 gained before its × counts as missed", (d, want_res))
    check("Ratés, au seau 0 et sans aucun sens : %s." % "、".join(ko) in more and "seau 1" not in more and d["back"] and counts() == []
          and page.evaluate(PRIMARY, "#done") == ["Reprendre la file"],
          S + "end screen: missed words, Reprendre la file (the only primary button)", more)
    check(d["text"] == "2 sur 5 réussis (40 %)." and "sans aucun sens :" in d["more"], S + "typography of the end screen", (d["text"], d["more"]))
    shot(page, "seaux-%s-16-sens-done" % scheme)
    check(page.evaluate(STARTFACE) == {"locked": "false", "checked": [str(ss()["setting"])]},
          S + "end screen: D’abord shows the setting again, unlocked", page.evaluate(STARTFACE))
    cs = page.evaluate("(W) => W.map(id => state.cards[id].kn)", W)
    check(cs == [0, 7, 7, 0, 0, 7], S + "ways known after the test (图书馆 lost the way gained in this same test)", cs)
    view("progress")
    check(kncounts() == [["Par le caractère", 3], ["Par le pinyin", 3], ["Par la traduction", 3], ["Les trois", 3]]
          and page.evaluate("() => document.querySelector('#sens-go').disabled")
          and nb(page.inner_text("#sens-info")) == "Aucun mot n’est connu dans un ou deux sens pour l’instant.",
          S + "Progrès after the test: counts follow, nothing left to test", kncounts())
    r = page.evaluate("() => { const m = study.mode; return [study.startSens(), m, study.mode, document.querySelector('#toast').textContent]; }")
    check(r[0] is False and r[1] == r[2] and r[3] == "Aucun mot à tester dans un nouveau sens : il faut des mots déjà connus dans un ou deux sens.",
          S + "startSens with nothing to test: a toast, nothing starts", r)

    # ------------------------------------------------------------ Arrêter
    page.evaluate("""(W) => { Object.assign(state.cards[W[1]], { kn: 1 }); Object.assign(state.cards[W[5]], { kn: 2 }); save(); }""", W)
    snap = ss()["snap"]
    go_sens()
    check(sorted(ss()["items"]) == sorted([[W[1], 1], [W[1], 2], [W[5], 0], [W[5], 2]]), S + "second test: 4 items", ss()["items"])
    rn = page.evaluate("""() => { const cur = study.cur, items = [[cur, study.curFace], ...study.queue.map(x => [x.id, x.face])];
        renameInStudy(cur, 'perso:今');
        return { cur, items, after: [[study.cur, study.curFace], ...study.queue.map(x => [x.id, x.face])] }; }""")
    check(rn["after"] == [["perso:今" if i == rn["cur"] else i, f] for i, f in rn["items"]],
          S + "a word that changes id keeps its ways to test (renameInStudy)", rn)
    page.click("#free-stop")
    page.wait_for_function("() => study.mode === 'line'")
    check(ss()["snap"] == snap and page.is_hidden("#free-note"), S + "Arrêter before any answer: back to the line, nothing changed")
    go_sens()
    pre = ss()
    a = answer(page, 1)
    page.click("#free-stop")
    d = done()
    check(d["title"] == "Test des sens arrêté" and nb(d["text"]) == "1 sur 1 réussi (100 %)." and [nb(x) for x in d["res"]] == ["Par %s1/1" % WAYS[pre["face"]]]
          and "Aucun mot raté." in nb(d["more"]) and d["back"],
          S + "Arrêter after one answer: Test des sens arrêté, partial results", d)
    b0 = page.evaluate(DONEBTNS)
    view("settings")
    page.click('#deck-settings .switch[data-deck="perso"]')
    view("study")
    b1 = page.evaluate(DONEBTNS)
    view("settings")
    page.click('#deck-settings .switch[data-deck="perso"]')
    view("study")
    b2 = page.evaluate(DONEBTNS)
    check(b0 == b2 == {"learn": True, "eval": True, "free": True} and b1 == {"learn": False, "eval": False, "free": False},
          S + "end screen: Apprendre, Évaluation and Libre follow the lists switched off and on", (b0, b1, b2))
    page.click("#done-back")
    page.wait_for_function("() => study.mode === 'line'")
    check(page.evaluate("(id) => state.cards[id].kn", a) == pre["card"]["kn"] | 1 << pre["face"], S + "the answer given before Arrêter stays")

    # a single word to test: the explanation in the singular
    page.evaluate("(W) => { for (const id of W) if (state.cards[id]) state.cards[id].kn = 0; state.cards[W[1]].kn = 1; save(); }", W)
    view("progress")
    info = nb(page.inner_text("#sens-info"))
    check(info.startswith("Un seul mot est connu dans un ou deux sens : le test le pose dans ceux qui lui manquent.") and "mots" not in info,
          S + "Progrès: the explanation agrees in the singular for 1 word", info)

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
        for scheme in ("light", "dark"):
            run_test_mode(browser, errors, scheme)
        for scheme in ("light", "dark"):
            run_knowledge(browser, errors, scheme)
            run_learning(browser, errors, scheme)
            run_sens(browser, errors, scheme)
        browser.close()
    finish(errors)


if __name__ == "__main__":
    main()
