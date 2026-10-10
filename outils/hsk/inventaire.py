# -*- coding: utf-8 -*-
"""Inventaire des mots HSK 2.0 (niveaux 1 à 6) et HSK 3.0 (programme 2026, niveaux 1 à 6).

Un mot = mêmes caractères, même prononciation, même sens : il n'apparaît qu'une fois et appartient
à toutes ses listes. Les mots déjà présents dans decks/hsk1-3.tsv gardent leur identifiant (donc leur
progression) ; les autres sont définis dans la première liste qui les contient (leur « maison »).

    py outils\\hsk\\inventaire.py          -> outils/hsk/inventaire.tsv et un résumé

Listes : hsk1 … hsk6 (HSK 2.0, liste officielle de 2012), hsk30-1 … hsk30-6 (HSK 3.0, 2026), publiées dans l'ordre
de ORDER : un mot est défini dans la première qui le contient.
Sources : outils/hsk/sources (voir LISEZMOI.md à côté).
"""
import io
import os
import re
import sys
from collections import OrderedDict, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))
import decks  # noqa: E402
from pinyin_auto import mark, join_word  # noqa: E402

OLD_IDS = ["hsk1", "hsk2", "hsk3", "hsk4", "hsk5", "hsk6"]
NEW_IDS = ["hsk30-%d" % i for i in range(1, 7)]
# publication order: a word is defined in the first published list that holds it (its id never changes afterwards)
ORDER = ["hsk1", "hsk2", "hsk3", "hsk30-1", "hsk30-2", "hsk30-3", "hsk4", "hsk30-4", "hsk5", "hsk30-5", "hsk6", "hsk30-6"]
# HSK 2.0 does not number homographs, HSK 3.0 does (花1 dépenser, 花2 fleur). By default a 2.0 entry is the first one;
# HOMO_OF: an existing word that is another one (its example sentence shows that sense);
# HOMO_IN: the homographs a 2.0 list holds, from the sense of its entry (both when it covers both).
HOMO_OF = {"hsk3:过去": "2"}
# errors of the 2012 list: 俩 (two people) reads liǎ (liǎng is only 伎俩 jìliǎng), as in the 2026 syllabus
SOURCE_FIX = {"俩": ("lia3", "liǎ")}
HOMO_IN = {("hsk2", "等"): "1", ("hsk4", "等"): "2", ("hsk3", "过去"): "2", ("hsk3", "花"): "12", ("hsk3", "站"): "12",
           ("hsk4", "省"): "12", ("hsk5", "称"): "12", ("hsk5", "批"): "12", ("hsk5", "升"): "12", ("hsk5", "所"): "12",
           ("hsk5", "支"): "12", ("hsk6", "乘"): "12", ("hsk6", "副"): "12", ("hsk6", "喂"): "12"}


def read_tsv(path):
    rows, head = [], None
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.rstrip("\r\n")
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if head is None:
            head = cells
            continue
        rows.append(dict(zip(head, cells + [""] * (len(head) - len(cells)))))
    return rows


def syls_numeric(numeric):
    """'ai4qing2', 'ba4 ba5' -> [('ai', 4), ('qing', 2)] ; sans chiffre ('de') : ton neutre."""
    s = numeric.lower().replace(" ", "").replace("'", "")
    if not re.search(r"\d", s):
        s += "5"
    return [(m.group(1).replace("u:", "v").replace("ü", "v"), int(m.group(2))) for m in re.finditer(r"([a-zü:v]+?)([1-5])", s)]


def syls_marked(p):
    """'túshūguǎn' -> [('tu', 2), ('shu', 1), ('guan', 3)] ; ton neutre 5."""
    out = []
    for syl in decks.syllables_of(p.strip()) or []:
        letters, tone = "", 5
        for ch in syl:
            base, t = decks.decode(ch)
            letters += base
            if t:
                tone = t
        out.append((letters.lower(), tone))
    return out


def key(h, syls):
    """Lettres et tons ; ceux de 一 et 不 ne comptent pas (yī, yí, yì : le même mot)."""
    return "".join(s for s, _ in syls), tuple(0 if (i < len(h) and h[i] in "一不") else t for i, (s, t) in enumerate(syls))


def same(h1, s1, h2, s2, loose=False):
    """Même mot écrit pareil et lu pareil ; loose : au ton neutre près (xuésheng / xuéshēng)."""
    if h1 != h2:
        return False
    a, b = key(h1, s1), key(h2, s2)
    if a[0] != b[0] or len(a[1]) != len(b[1]):
        return False
    return all(x == y or 0 in (x, y) or (loose and 5 in (x, y)) for x, y in zip(a[1], b[1]))


def sandhi(h, syls):
    """Le 一 et le 不 avec leur ton réel (yídìng, yìqǐ, búcuò) ; un 一 final, ou après 第 ou un nombre, reste yī."""
    out = list(syls)
    for i, (s, t) in enumerate(syls):
        ch = h[i] if i < len(h) else ""
        if i + 1 >= len(syls) or ch not in "一不":
            continue
        nxt = syls[i + 1][1]
        if ch == "一":
            if i > 0 and h[i - 1] in "第十二三四五六七八九百千万零统唯":
                continue
            out[i] = (s, 2 if nxt == 4 else 4 if nxt in (1, 2, 3) else 1)
        elif nxt == 4:
            out[i] = (s, 2)
    return out


def display(h, syls):
    return join_word([mark(s + str(t)) for s, t in sandhi(h, syls)])


words = []                                     # every word, in creation order


def add(h, syls, home, state, **kw):
    w = {"h": h, "syls": syls, "home": home, "state": state, "lists": [], "old": [], "new": [], "en": [], "pos": "", "num": "",
         "id": "", "pinyin": "", "of": None}
    w.update(kw)
    words.append(w)
    return w


def member(w, lid, en=""):
    if lid not in w["lists"]:
        w["lists"].append(lid)
    lv = int(lid.split("-")[-1]) if lid.startswith("hsk30") else int(lid[3:])
    bag = w["new"] if lid.startswith("hsk30") else w["old"]
    if lv not in bag:
        bag.append(lv)
    if en and en not in w["en"]:
        w["en"].append(en)


# ---------- the existing lists (hsk1-3): they keep their ids and their membership
for lid in ("hsk1", "hsk2", "hsk3"):
    count = defaultdict(int)
    for r in read_tsv(os.path.join(ROOT, "decks", lid + ".tsv")):
        h = r["hanzi"]
        count[h] += 1
        reads = [x.strip() for x in r["pinyin"].split("/")]
        w = add(h, syls_marked(reads[0]), lid, "existant", id="%s:%s%s" % (lid, h, "#%d" % count[h] if count[h] > 1 else ""),
                pinyin=reads[0], fr=r["francais"])
        member(w, lid)
        for extra in reads[1:]:              # 只 zhǐ / zhī, 地 de / dì : la seconde lecture devient un mot à part
            x = add(h, syls_marked(extra), lid, "scission", pinyin=extra, of=w, fr=r["francais"])
            member(x, lid)


def find(h, syls, loose=False, skip=()):
    return [w for w in words if id(w) not in skip and same(w["h"], w["syls"], h, syls, loose)]


# ---------- HSK 2.0 (2012): levels 1-3 give the official reading of the existing words; levels 4-6 are new lists
for r in read_tsv(os.path.join(HERE, "sources", "hsk2012.tsv")):
    lv, h = int(r["niveau"]), r["mot"]
    if h in SOURCE_FIX:
        r["numerique"], r["pinyin"] = SOURCE_FIX[h]
    nums = [x.strip() for x in r["numerique"].split(",")]
    marks = [x.strip() for x in r["pinyin"].split(",")]
    ens = [x.strip() for x in r["anglais"].split("|")]
    if len(ens) != len(nums):
        ens = [r["anglais"]] * len(nums)
    for i, num in enumerate(nums):
        # the marked pinyin: the numbered one of this source leaves the neutral tone without a digit (xiao1xi)
        syls = syls_marked(marks[i]) if i < len(marks) else []
        if len(syls) != len(re.sub(r"[^一-鿿]", "", h)) and not h.endswith("儿"):
            syls = syls_numeric(num) if len(syls_numeric(num)) == len(h) else syls
        hit = find(h, syls)
        if lv <= 3:
            for w in hit:
                if w["state"] in ("existant", "scission") and ens[i] not in w["en"]:
                    w["en"].append(ens[i])
            continue
        w = hit[0] if hit else add(h, syls, "hsk%d" % lv, "nouveau", p2012=marks[i] if i < len(marks) else "")
        member(w, "hsk%d" % lv, ens[i])

# ---------- HSK 3.0 (2026): one entry per number; a word listed at several levels (other uses) is one entry
entries = OrderedDict()
for r in read_tsv(os.path.join(HERE, "sources", "hsk2026.tsv")):
    e = entries.get(r["entree"])
    if e:
        e["lvs"].append(int(r["niveau"]))
        if r["nature"] and r["nature"] not in e["pos"]:
            e["pos"] = (e["pos"] + "、" if e["pos"] else "") + r["nature"]
        continue
    m = re.match(r"^(.*?)(\d*)$", r["mot"])
    # two readings of one word (谁 shéi/shuí): the first one to compare, both to show
    entries[r["entree"]] = {"h": m.group(1), "num": m.group(2), "syls": syls_numeric(r["numerique"].split("/")[0]), "p": r["pinyin"],
                           "lvs": [int(r["niveau"])], "pos": r["nature"], "en": r["anglais"],
                           "alt": r["pinyin"].replace("/", " / ") if "/" in r["pinyin"] else ""}
taken, pending, loose_hits = set(), [], []
byword = {w["id"]: w for w in words if w["id"]}


def attach(w, e):
    taken.add(id(w))
    for lv in e["lvs"]:
        member(w, "hsk30-%d" % lv, e["en"])
    w["pos"] = e["pos"]
    w["num"] = w["num"] or e["num"]
    w["p2026"] = e["p"]
    if e.get("alt"):
        w["alt"] = e["alt"]


forced = {}
for wid, num in HOMO_OF.items():
    w = byword[wid]
    e = next(e for e in entries.values() if e["h"] == w["h"] and e["num"] == num)
    forced[id(e)] = w
    taken.add(id(w))
for e in entries.values():                   # same reading first: 2012 and the existing lists
    if id(e) in forced:
        attach(forced[id(e)], e)
        continue
    hit = find(e["h"], e["syls"], skip=taken)
    if hit:
        attach(hit[0], e)
    else:
        pending.append(e)
for e in pending:                            # then the same reading but for neutral tones
    hit = find(e["h"], e["syls"], loose=True, skip=taken)
    if hit:
        loose_hits.append((hit[0]["h"], hit[0].get("pinyin") or hit[0].get("p2012"), e["p"]))
        attach(hit[0], e)
        continue
    w = add(e["h"], e["syls"], "hsk30-%d" % min(e["lvs"]), "nouveau")
    twins = [x for x in words if x is not w and x["h"] == e["h"] and x["num"] and e["num"] and same(x["h"], x["syls"], e["h"], e["syls"])]
    if twins:                                # 点1 / 点2 : un homographe, d'un autre sens
        w["state"], w["of"] = "homographe", twins[0]
        twins[0]["of"] = twins[0]["of"] or w     # each one names the other (lots : colonne lie_a)
    attach(w, e)

# ---------- which homograph a 2.0 list holds (HOMO_IN)
for (lid, h), nums in HOMO_IN.items():
    lv = int(lid[3:])
    group = [w for w in words if w["h"] == h and w["num"]]
    assert {w["num"] for w in group} >= set(nums), (lid, h)
    for w in group:
        if w["num"] in nums:
            member(w, lid)
        elif lid in w["lists"]:
            w["lists"].remove(lid)
            w["old"].remove(lv)

# ---------- pinyin to show, ids (what the app derives: <list>:<hanzi>, #2 … for the same hanzi further down the file)
seen_in = defaultdict(lambda: defaultdict(int))
for w in words:                              # existing rows first (they come first in their files)
    if w["state"] == "existant":
        seen_in[w["home"]][w["h"]] += 1
for w in words:
    w["lists"].sort(key=ORDER.index)
    if w["state"] == "existant":
        continue
    if w["state"] != "scission":
        w["home"] = w["lists"][0]
    if w["state"] != "scission":
        w["pinyin"] = w.get("alt") or display(w["h"], w["syls"])
    seen_in[w["home"]][w["h"]] += 1
    k = seen_in[w["home"]][w["h"]]
    w["id"] = "%s:%s%s" % (w["home"], w["h"], "#%d" % k if k > 1 else "")
ids = defaultdict(int)
for w in words:
    ids[w["id"]] += 1
assert all(v == 1 for v in ids.values()), [k for k, v in ids.items() if v > 1]

out = io.open(os.path.join(HERE, "inventaire.tsv"), "w", encoding="utf-8", newline="\n")
out.write("# Inventaire des mots HSK, produit par outils/hsk/inventaire.py : ne pas modifier à la main.\n")
out.write("# etat : existant (decks/hsk1-3), nouveau, scission (seconde lecture d'un mot existant), homographe (autre sens, même écriture).\n")
out.write("\t".join(["id", "mot", "pinyin", "homographe", "hsk20", "hsk30", "listes", "maison", "etat", "nature", "anglais", "lie_a"]) + "\n")
for w in sorted(words, key=lambda w: ORDER.index(w["home"])):
    out.write("\t".join([w["id"], w["h"], w["pinyin"], w["num"], " ".join(map(str, sorted(w["old"]))), " ".join(map(str, sorted(w["new"]))),
                         " ".join(w["lists"]), w["home"], w["state"], w["pos"], " | ".join(w["en"]).replace("\t", " ")[:400],
                         w["of"]["id"] if w["of"] else ""]) + "\n")
out.close()

by = defaultdict(int)
for w in words:
    by[w["state"]] += 1
print("mots :", len(words), dict(by))
print("au ton neutre près :", len(loose_hits), loose_hits[:12])
per = defaultdict(int)
for w in words:
    for l in w["lists"]:
        per[l] += 1
print("par liste :", {l: per[l] for l in ORDER})
home = defaultdict(int)
for w in words:
    if w["state"] != "existant":
        home[w["home"]] += 1
print("à rédiger, par maison :", {l: home[l] for l in ORDER if home[l]})
print("existants sans lecture HSK 2.0 retrouvée :", [w["id"] for w in words if w["state"] == "existant" and not w["en"]])
print("existants absents du HSK 3.0 :", sum(1 for w in words if w["state"] == "existant" and not w["new"]))
