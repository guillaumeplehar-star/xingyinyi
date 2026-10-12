# -*- coding: utf-8 -*-
"""Ordre des traits : extrait de Make Me a Hanzi (graphics.txt) pour les caractères de l'appli.

    py outils\\traits.py <chemin de graphics.txt>

graphics.txt (github.com/skishore/makemeahanzi, licence Arphic Public License) n'est pas gardé dans le dépôt :
télécharge-le, puis lance cette commande. Elle écrit traits/00.json … traits/31.json (les caractères rangés par
code % 32 : { "爱": [[contours SVG des traits], [lignes médianes : [[x, y], …], …]] }, repère de 1024 sur 1024, y vers
le haut, base à 900), traits/index.json (version des données, nombre de paquets et de caractères) et copie la
licence ARPHICPL.TXT à côté. Les caractères sont ceux de la police de l'appli (COVER dans index.html).
"""
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "traits")
PACKS = 32


def cover():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'const COVER = new Set\("([^"]*)"\)', html)
    if not m:
        sys.exit("COVER introuvable dans index.html")
    return {c for c in m.group(1) if 0x3400 <= ord(c) <= 0x9FFF}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    lic = os.path.join(os.path.dirname(os.path.abspath(src)), "ARPHICPL.TXT")
    if not os.path.exists(lic):
        sys.exit("Il manque ARPHICPL.TXT (la licence Arphic Public License) à côté de graphics.txt.")
    want = cover()
    packs = [dict() for _ in range(PACKS)]
    with open(src, encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            c = d["character"]
            if c in want:
                packs[ord(c) % PACKS][c] = [d["strokes"], d["medians"]]
    found = {c for p in packs for c in p}
    os.makedirs(OUT, exist_ok=True)
    digest, total = hashlib.sha1(), 0
    for i, p in enumerate(packs):
        text = json.dumps(dict(sorted(p.items())), ensure_ascii=False, separators=(",", ":"))
        digest.update(text.encode("utf-8"))
        total += len(text.encode("utf-8"))
        with open(os.path.join(OUT, "%02d.json" % i), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    index = {"v": digest.hexdigest()[:10], "paquets": PACKS, "caracteres": len(found),
             "source": "Make Me a Hanzi, graphics.txt (github.com/skishore/makemeahanzi), licence Arphic Public License (ARPHICPL.TXT)"}
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(index, ensure_ascii=False, indent=1) + "\n")
    with open(lic, "rb") as a, open(os.path.join(OUT, "ARPHICPL.TXT"), "wb") as b:
        b.write(a.read())
    missing = sorted(want - found)
    print("traits/ : %d caractères sur %d, %d paquets, %.1f Mo, version %s" % (len(found), len(want), PACKS, total / 1e6, index["v"]))
    if missing:
        print("sans données : " + "".join(missing))


if __name__ == "__main__":
    main()
