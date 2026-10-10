# -*- coding: utf-8 -*-
"""Relecture des fiches existantes (decks/hsk1-3.tsv) avec les mêmes outils que les nouvelles.

    py outils\\hsk\\revue.py exporter     -> lots r01-hsk1 … dans outils/hsk/travail/lots et rediges (fiches actuelles)

Les phrases de ces listes n'emploient que des caractères HSK 1-3 : le contrôle les juge au niveau 3 du HSK 2.0.
Les corrections reviennent dans decks/ avec outils/hsk/assembler.py.
"""
import io
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
WORK = os.path.join(HERE, "travail")
COLS = ["id", "mot", "pinyin", "francais", "note", "audio", "exemple", "exemple_pinyin", "exemple_fr"]


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


def exporter(size=76):
    inv = {r["id"]: r for r in read_tsv(os.path.join(HERE, "inventaire.tsv"))}
    n = 0
    for lid in ("hsk1", "hsk2", "hsk3"):
        rows, count = [], defaultdict(int)
        for r in read_tsv(os.path.join(ROOT, "decks", lid + ".tsv")):
            count[r["hanzi"]] += 1
            k = count[r["hanzi"]]
            r["id"] = "%s:%s%s" % (lid, r["hanzi"], "#%d" % k if k > 1 else "")
            rows.append(r)
        for i in range(0, len(rows), size):
            n += 1
            name = "r%02d-%s" % (n, lid)
            with io.open(os.path.join(WORK, "lots", name + ".tsv"), "w", encoding="utf-8", newline="\n") as out:
                out.write("id\tmot\tpinyin\thomographe\tnature\tniveaux\tanglais\tlie_a\n")
                for r in rows[i:i + size]:
                    iv = inv.get(r["id"], {})
                    out.write("\t".join([r["id"], r["hanzi"], r["pinyin"], "", iv.get("nature", ""), "2.0:3", iv.get("anglais", ""), ""]) + "\n")
            with io.open(os.path.join(WORK, "rediges", name + ".tsv"), "w", encoding="utf-8", newline="\n") as out:
                out.write("\t".join(COLS) + "\n")
                for r in rows[i:i + size]:
                    vals = [r["id"], r["hanzi"], r["pinyin"], r["francais"], r["note"], r["audio"], r["exemple"], r["exemple_pinyin"], r["exemple_fr"]]
                    out.write("\t".join(v.replace("\t", " ") for v in vals) + "\n")
    print("%d lots de relecture" % n)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "exporter":
        exporter()
    else:
        print(__doc__)
