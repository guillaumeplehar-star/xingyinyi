#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Après une modification de l'appli (index.html, icônes, manifeste, polices) :

    py outils\\version_appli.py          (python3 outils/version_appli.py sur Mac ou Linux)

1. met à jour la date affichée dans Réglages › Appli (« Version du … ») ;
2. recalcule la version du service worker (sw.js) et sa liste de fichiers gardés hors ligne.

Le service worker change donc dès que l'appli change : les téléphones affichent alors
« Nouvelle version de l'appli prête » au lieu de garder l'ancienne copie.
Inutile après une simple modification des listes de mots (decks/) : elles se mettent à jour seules.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:   # garde les fins de ligne telles quelles (CRLF sous Windows)
        return fh.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    index, sw = os.path.join(ROOT, "index.html"), os.path.join(ROOT, "sw.js")
    d = datetime.now()
    label = "%d%s %s %d à %d h %02d" % (d.day, "er" if d.day == 1 else "", MOIS[d.month - 1], d.year, d.hour, d.minute)
    html, n = re.subn(r'const BUILD = "[^"]*";', 'const BUILD = "%s";' % label, read(index), count=1)
    if n != 1:
        sys.exit("index.html : ligne « const BUILD = \"…\"; » introuvable.")
    write(index, html)

    text = read(sw)
    core = json.loads(re.search(r"const CORE = (\[.*?\]);", text).group(1))
    extra = json.loads(re.search(r"const EXTRA = (\[.*?\]);", text).group(1))
    fonts = sorted("fonts/" + f for f in os.listdir(os.path.join(ROOT, "fonts")) if f.endswith(".woff2"))
    config = json.loads(read(os.path.join(ROOT, "decks", "decks.json")))
    decks = ["decks/decks.json"] + ["decks/" + l["fichier"] for l in config.get("listes", []) if l.get("fichier")]
    extra = fonts + list(dict.fromkeys(decks))
    missing = [rel for rel in core if not os.path.exists(os.path.join(ROOT, rel))]
    if missing:
        sys.exit("Fichiers de l'appli introuvables : " + ", ".join(missing))
    h = hashlib.sha1()
    for rel in core + fonts:
        with open(os.path.join(ROOT, rel), "rb") as fh:
            h.update(fh.read())
    version = h.hexdigest()[:10]
    text = re.sub(r'const VERSION = "[^"]*";', 'const VERSION = "%s";' % version, text, count=1)
    text = re.sub(r"const EXTRA = \[.*?\];", "const EXTRA = %s;" % json.dumps(extra), text, count=1)
    write(sw, text)
    print("Appli : version du %s, service worker %s." % (label, version))
    print("Pour publier :\n  git add -A\n  git commit -m \"Nouvelle version de l'appli\"\n  git push")


if __name__ == "__main__":
    main()
