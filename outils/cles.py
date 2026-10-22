# -*- coding: utf-8 -*-
"""Clés (部首) des caractères de l'appli, pour la recherche par clé de Mots.

Lit la base Unihan d'Unicode (https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip, décompressé ; licence Unicode,
https://www.unicode.org/license.txt) : kRSUnicode (clé du Kangxi, ' pour sa forme simplifiée, et traits restants) et
kTotalStrokes ; et CJKRadicals.txt (même adresse) : le caractère de chaque clé. Les caractères : ceux de la police de
l'appli (COVER dans index.html) et ceux de la colonne hanzi des listes de decks/. Écrit dans index.html la constante
CLES : [numéro de la clé, formes montrées (la première en grand), traits de la clé, {traits restants: caractères}],
triée par traits de la clé puis par numéro.

  py outils\\cles.py <dossier Unihan décompressé> <CJKRadicals.txt>
"""
import io
import json
import os
import re
import sys

for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAN = re.compile(r"[㐀-鿿豈-﫿]")
# Forms a key takes in a character (亻 for 人…), the usual one first: the forms the learner sees
FORMS = {"9": "亻人", "18": "刂刀", "61": "忄心", "64": "扌手", "66": "攵攴", "85": "氵水", "86": "灬火", "87": "爫爪",
         "93": "牜牛", "94": "犭犬", "96": "王玉", "113": "礻示", "122": "罒网", "130": "月肉", "140": "艹艸", "145": "衤衣",
         "162": "辶辵", "163": "阝邑", "170": "阝阜"}
# Strokes of these forms in today's dictionaries of simplified characters (Unihan counts them as the older forms)
STROKES = {"艹": 3, "辶": 3, "阝": 2, "礻": 4, "衤": 5}


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    unihan, radicals = sys.argv[1], sys.argv[2]
    rs, strokes = {}, {}
    for name in os.listdir(unihan):
        if not name.startswith("Unihan_") or not name.endswith(".txt"):
            continue
        with io.open(os.path.join(unihan, name), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or "\t" not in line:
                    continue
                cp, field, value = line.rstrip("\n").split("\t", 2)
                ch = chr(int(cp[2:], 16))
                if field == "kRSUnicode":
                    rs[ch] = value.split()[0]
                elif field == "kTotalStrokes":
                    strokes[ch] = int(value.split()[0])
    form = {}
    with io.open(radicals, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or ";" not in line:
                continue
            num, _, ideo = [x.strip() for x in line.split(";")]
            if ideo:
                form[num] = chr(int(ideo, 16))
    if not rs or not form:
        sys.exit("kRSUnicode ou CJKRadicals introuvables : vérifie les deux chemins.")

    html = io.open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'const COVER = new Set\("([^"]*)"\)', html)
    if not m:
        sys.exit("COVER introuvable dans index.html")
    chars = set(m.group(1))
    decks = os.path.join(ROOT, "decks")
    for name in os.listdir(decks):
        if name.endswith(".tsv"):
            with io.open(os.path.join(decks, name), encoding="utf-8") as fh:
                for line in fh:
                    chars.update(HAN.findall(re.split(r"\t| {2,}", line.strip(), 1)[0]))
    chars = {c for c in chars if HAN.match(c)}

    keys, missing = {}, []
    for ch in sorted(chars):
        if ch not in rs:
            missing.append(ch)
            continue
        num, rest = rs[ch].split(".")
        keys.setdefault(num, {}).setdefault(int(rest), []).append(ch)
    out = []
    for num, by in keys.items():
        shown = FORMS.get(num, form.get(num, ""))
        if not shown:
            missing.extend(c for cs in by.values() for c in cs)
            continue
        n = STROKES.get(shown[0], strokes.get(shown[0], 0))
        out.append([num, shown, n, {str(r): "".join(sorted(cs, key=lambda c: (strokes.get(c, 99), c))) for r, cs in sorted(by.items())}])
    out.sort(key=lambda k: (k[2], int(k[0].rstrip("'")), k[0]))

    line = "const CLES = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    new, n = re.subn(r"^const CLES = .*;$", lambda _: line, html, count=1, flags=re.M)
    if not n:
        sys.exit("const CLES = …; introuvable dans index.html (une ligne à elle seule)")
    io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8", newline="").write(new)
    total = sum(len(cs) for k in out for cs in k[3].values())
    print("%d clés, %d caractères écrits dans index.html (CLES)." % (len(out), total))
    if missing:
        print("Sans clé connue (%d) : %s" % (len(missing), "".join(missing[:60])))


if __name__ == "__main__":
    main()
