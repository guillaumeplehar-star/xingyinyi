# -*- coding: utf-8 -*-
"""Découpe les mots à rédiger de outils/hsk/inventaire.tsv en lots (outils/hsk/travail/lots/NNN-maison.tsv).

    py outils\\hsk\\lots.py [taille]        (60 mots par lot par défaut)

Les mots existants (decks/hsk1-3) ne sont pas à rédiger : ils sont relus à part (lots revue-hsk1 …).
"""
import io
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "travail", "lots")
# the lists most useful first: HSK 4 (2.0), the first levels of HSK 3.0, then the others
PRIORITY = ["hsk3", "hsk30-1", "hsk30-2", "hsk30-3", "hsk4", "hsk30-4", "hsk5", "hsk30-5", "hsk6", "hsk30-6"]   # publication order


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


def main():
    size = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    inv = read_tsv(os.path.join(HERE, "inventaire.tsv"))
    freq = {r["mot"]: int(r["rang"]) for r in read_tsv(os.path.join(HERE, "sources", "frequence.tsv"))}
    byid = {r["id"]: r for r in inv}
    # the French of the existing words, for the homographs and second readings that sit next to them
    fr = {}
    for lid in ("hsk1", "hsk2", "hsk3"):
        count = defaultdict(int)
        for r in read_tsv(os.path.join(ROOT, "decks", lid + ".tsv")):
            count[r["hanzi"]] += 1
            k = count[r["hanzi"]]
            fr["%s:%s%s" % (lid, r["hanzi"], "#%d" % k if k > 1 else "")] = r["francais"]
    # words already written (outils/hsk/travail/rediges): their lots stay, the new lots number on after them
    done, kept, n = set(), set(), 0
    red = os.path.join(HERE, "travail", "rediges")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(red, exist_ok=True)
    for f in sorted(os.listdir(red)):
        if f.endswith(".tsv") and f[:3].isdigit():
            kept.add(f)
            n = max(n, int(f[:3]))
            for r in read_tsv(os.path.join(red, f)):
                done.add((r["mot"], r["pinyin"]))
    for f in os.listdir(OUT):
        if f not in kept and not f.startswith("r"):
            os.remove(os.path.join(OUT, f))
    todo = defaultdict(list)
    for r in inv:
        if r["etat"] != "existant" and (r["mot"], r["pinyin"]) not in done:
            todo[r["maison"]].append(r)
    first = n
    head = ["id", "mot", "pinyin", "homographe", "nature", "niveaux", "anglais", "lie_a"]
    for home in PRIORITY:
        rows = sorted(todo.get(home, []), key=lambda r: freq.get(r["mot"], 10 ** 6))
        for i in range(0, len(rows), size):
            n += 1
            name = "%03d-%s.tsv" % (n, home)
            with io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as out:
                out.write("\t".join(head) + "\n")
                for r in rows[i:i + size]:
                    lv = " ".join(["2.0:" + x for x in r["hsk20"].split()] + ["3.0:" + x for x in r["hsk30"].split()])
                    rel = ""
                    if r["lie_a"]:
                        o = byid.get(r["lie_a"], {})
                        rel = "%s %s %s" % (r["lie_a"], o.get("pinyin", ""), fr.get(r["lie_a"], "(à rédiger dans un autre lot)"))
                    out.write("\t".join([r["id"], r["mot"], r["pinyin"], r["homographe"], r["nature"], lv, r["anglais"], rel]) + "\n")
    print("%d mots déjà rédigés ; %d nouveaux lots de %d mots au plus dans %s" % (len(done), n - first, size, os.path.relpath(OUT, ROOT)))


if __name__ == "__main__":
    main()
