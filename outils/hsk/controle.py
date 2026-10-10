# -*- coding: utf-8 -*-
"""Contrôle d'un lot rédigé (outils/hsk/travail/rediges/<lot>.tsv) et pinyin des phrases d'exemple.

    py outils\\hsk\\controle.py 001-hsk4            contrôle, et remplit la colonne exemple_pinyin
    py outils\\hsk\\controle.py 001-hsk4 --garder    contrôle sans toucher au pinyin des phrases déjà rempli

Vérifie : chaque mot du lot présent une fois, sens rempli, phrase qui contient le mot, caractères de la phrase
du niveau du mot ou en dessous (HSK 2.0 ou HSK 3.0), ponctuation, longueur, traduction de la phrase.
Sortie : une ligne par problème (ERREUR ou attention) ; code 1 s'il reste une ERREUR.
"""
import io
import os
import re
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pinyin_auto  # noqa: E402

COLS = ["id", "mot", "pinyin", "francais", "note", "audio", "exemple", "exemple_pinyin", "exemple_fr"]
HAN = re.compile(r"[㐀-鿿]")
ZH_PUNCT = set("，。？！、：；“”‘’（）《》…—·")


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
    return head, rows


def level_chars():
    """Caractères permis par niveau : HSK 2.0 (2012) niveaux ≤ n, HSK 3.0 (2026) niveaux ≤ n."""
    old, new = defaultdict(set), defaultdict(set)
    for r in read_tsv(os.path.join(HERE, "sources", "hsk2012.tsv"))[1]:
        old[int(r["niveau"])] |= set(HAN.findall(r["mot"]))
    for r in read_tsv(os.path.join(HERE, "sources", "hsk2026.tsv"))[1]:
        new[int(r["niveau"])] |= set(HAN.findall(re.sub(r"\d", "", r["mot"])))
    cum_old = {n: set().union(*[old[i] for i in range(1, n + 1)]) for n in range(1, 7)}
    cum_new = {n: set().union(*[new[i] for i in range(1, n + 1)]) for n in range(1, 7)}
    return cum_old, cum_new


def allowed_for(levels, cum_old, cum_new):
    """levels : '2.0:4 3.0:3 3.0:5' -> caractères du plus bas niveau dans chaque version."""
    o = [int(x[4:]) for x in levels.split() if x.startswith("2.0:")]
    n = [int(x[4:]) for x in levels.split() if x.startswith("3.0:")]
    s = set()
    if o:
        s |= cum_old[min(o)]
    if n:
        s |= cum_new[min(n)]
    if not s:
        s = cum_old[3]
    return s


def contains(sentence, word):
    if word in sentence:
        return "oui"
    # separable words (帮忙 -> 帮了我一个忙): every character, in order
    i = 0
    for ch in word:
        j = sentence.find(ch, i)
        if j < 0:
            return "non"
        i = j + 1
    return "séparé"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    lot = sys.argv[1].replace(".tsv", "")
    keep = "--garder" in sys.argv
    src = os.path.join(HERE, "travail", "lots", lot + ".tsv")
    dst = os.path.join(HERE, "travail", "rediges", lot + ".tsv")
    if not os.path.exists(dst):
        print("ERREUR : %s n'existe pas" % os.path.relpath(dst))
        return 1
    _, want = read_tsv(src)
    head, rows = read_tsv(dst)
    missing_cols = [c for c in COLS if c not in head]
    problems = []
    if missing_cols:
        problems.append(("ERREUR", "-", "colonnes manquantes : " + ", ".join(missing_cols)))
    cum_old, cum_new = level_chars()
    lex = pinyin_auto.load_lexicon(os.path.join(os.path.dirname(HERE), "lexique_hsk.tsv"),
                                   os.path.join(os.path.dirname(HERE), "lexique_complements.tsv"))
    byid = {}
    for r in rows:
        if r.get("id") in byid:
            problems.append(("ERREUR", r.get("id"), "ligne en double"))
        byid[r.get("id")] = r
    for w in want:
        r = byid.get(w["id"])
        wid = w["id"]
        if not r:
            problems.append(("ERREUR", wid, "mot absent du fichier rédigé"))
            continue
        if r.get("mot") != w["mot"]:
            problems.append(("ERREUR", wid, "caractères changés : %s -> %s" % (w["mot"], r.get("mot"))))
        if r.get("pinyin") != w["pinyin"]:
            problems.append(("attention", wid, "pinyin du mot changé : %s -> %s (à justifier dans la note de relecture)" % (w["pinyin"], r.get("pinyin"))))
        f, e, ef = r.get("francais", ""), r.get("exemple", ""), r.get("exemple_fr", "")
        if not f:
            problems.append(("ERREUR", wid, "sens en français vide"))
        if HAN.search(f) and "=" not in f and "(" not in f:
            problems.append(("attention", wid, "caractères chinois dans le sens sans « = » ni parenthèses"))
        if re.search(r"\s;\S|\S;\s|\S;\S", f):
            problems.append(("attention", wid, "sens à séparer par « ; » entouré d'espaces"))
        if not e:
            problems.append(("ERREUR", wid, "phrase d'exemple vide"))
            continue
        c = contains(e, w["mot"])
        if c == "non":
            problems.append(("ERREUR", wid, "la phrase ne contient pas le mot %s" % w["mot"]))
        elif c == "séparé":
            problems.append(("attention", wid, "mot séparé dans la phrase (verbe séparable ?) : vérifier"))
        allowed = allowed_for(w["niveaux"], cum_old, cum_new) | set(HAN.findall(w["mot"]))
        bad = [ch for ch in HAN.findall(e) if ch not in allowed]
        if bad:
            problems.append(("ERREUR", wid, "caractères hors niveau dans la phrase : %s" % "".join(dict.fromkeys(bad))))
        other = [ch for ch in e if not HAN.match(ch) and ch not in ZH_PUNCT and not ch.isdigit()]
        if other:
            problems.append(("ERREUR", wid, "caractères non chinois dans la phrase : %r" % "".join(other)))
        if e[-1] not in "。？！…":
            problems.append(("ERREUR", wid, "la phrase doit finir par 。 ？ ！ ou …"))
        n = len(HAN.findall(e))
        if n > 28:
            problems.append(("ERREUR", wid, "phrase trop longue (%d caractères, 28 au plus)" % n))
        elif n < 4:
            problems.append(("attention", wid, "phrase très courte (%d caractères)" % n))
        if not ef:
            problems.append(("ERREUR", wid, "traduction de la phrase vide"))
        else:
            if HAN.search(ef):
                problems.append(("ERREUR", wid, "caractères chinois dans la traduction"))
            if ef[-1] not in ".?!…»":
                problems.append(("ERREUR", wid, "la traduction doit finir par . ? ! ou …"))
            if "'" in ef or "'" in f or "'" in r.get("note", ""):
                problems.append(("ERREUR", wid, "apostrophe droite ' : écrire ’"))
            if re.search(r"\S[?!:;]", ef):
                problems.append(("attention", wid, "espace attendue avant ? ! : ;"))
        if not keep or not r.get("exemple_pinyin"):
            r["exemple_pinyin"] = pinyin_auto.sentence_pinyin(e, lex)
        if len(w["mot"]) == 1 and not r.get("audio"):
            problems.append(("attention", wid, "mot d'un caractère sans audio : la voix peut choisir une autre lecture"))
    extra = [r.get("id") for r in rows if r.get("id") not in {w["id"] for w in want}]
    for x in extra:
        problems.append(("ERREUR", x, "mot qui n'est pas dans le lot"))
    # rewrite with the columns in order and the example pinyin
    with io.open(dst, "w", encoding="utf-8", newline="\n") as out:
        out.write("\t".join(COLS) + "\n")
        order = {w["id"]: i for i, w in enumerate(want)}
        for r in sorted(rows, key=lambda r: order.get(r.get("id"), 10 ** 6)):
            out.write("\t".join((r.get(k) or "").replace("\t", " ").strip() for k in COLS) + "\n")
    errs = [p for p in problems if p[0] == "ERREUR"]
    for p in problems:
        print("%s\t%s\t%s" % p)
    print("%s : %d mots, %d erreurs, %d points d'attention" % (lot, len(want), len(errs), len(problems) - len(errs)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
