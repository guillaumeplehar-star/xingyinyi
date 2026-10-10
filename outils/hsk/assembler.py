# -*- coding: utf-8 -*-
"""Écrit les listes HSK de decks/ à partir de l'inventaire et des fiches rédigées et relues.

    py outils\\hsk\\assembler.py            état des listes, sans rien écrire
    py outils\\hsk\\assembler.py --ecrire   écrit decks/ (listes complètes, dans l'ordre de publication)

- Les fiches relues (journal outils/hsk/travail/journal/<lot>.revue.txt terminé par RELU) des mots existants
  corrigent decks/hsk1-3.tsv ; les secondes lectures (只 zhī, 地 dì) et les homographes d'un mot existant que la
  liste 2.0 contient aussi (花 fleur à côté de 花 dépenser) y sont ajoutés à la suite.
- Une liste nouvelle n'est écrite que si tous ses mots ont une fiche relue, et seulement si les listes qui la
  précèdent dans l'ordre de publication le sont aussi : un mot est défini dans la première liste publiée qui
  le contient (inventaire, colonne maison) ; les autres listes y renvoient par ses caractères (et son pinyin
  quand il le faut, ou son identifiant pour deux homographes).
- decks.json : les listes HSK sont « fixe » (le téléphone ne peut pas les modifier) ; les nouvelles sont
  inactives et masquées au départ (« actif » et « afficher » à false).
"""
import io
import json
import os
import sys
from collections import OrderedDict, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DECKS = os.path.join(ROOT, "decks")
WORK = os.path.join(HERE, "travail")
sys.path.insert(0, os.path.dirname(HERE))
import decks as dk  # noqa: E402

ORDER = ["hsk1", "hsk2", "hsk3", "hsk30-1", "hsk30-2", "hsk30-3", "hsk4", "hsk30-4", "hsk5", "hsk30-5", "hsk6", "hsk30-6"]
NAMES = {"hsk1": "HSK 1 (2.0)", "hsk2": "HSK 2 (2.0)", "hsk3": "HSK 3 (2.0)", "hsk4": "HSK 4 (2.0)", "hsk5": "HSK 5 (2.0)",
         "hsk6": "HSK 6 (2.0)", **{"hsk30-%d" % i: "HSK %d (3.0)" % i for i in range(1, 7)}}
COLS = ["hanzi", "pinyin", "francais", "note", "audio", "exemple", "exemple_pinyin", "exemple_fr"]
FIELDS = ["pinyin", "francais", "note", "audio", "exemple", "exemple_pinyin", "exemple_fr"]
# the second reading, or the other homograph, now has its own sheet: the first word keeps only its own sense
SPLIT = {"hsk3:只": {"pinyin": "zhǐ", "francais": "seulement, ne… que"},
         "hsk3:地": {"pinyin": "de", "francais": "particule adverbiale ≈ ‑ment : 认真地学习 = étudier sérieusement"},
         "hsk3:花": {"francais": "dépenser (argent, temps)", "note": "à distinguer de 花 huā (fleur)"},
         "hsk3:站": {"francais": "station, arrêt", "note": "à distinguer de 站 zhàn (se tenir debout)"},
         "hsk3:过去": {"francais": "le passé, autrefois", "note": "à distinguer de 过去 guòqù (passer, aller là-bas)"},
         "hsk2:等": {"francais": "attendre ; (等…再…) quand, une fois que : 等我吃完饭再去 = j’irai quand j’aurai fini de manger",
                   "note": "à distinguer de 等 děng (etc. ; rang, classe)"}}


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


def reviewed(lot):
    j = os.path.join(WORK, "journal", lot + ".revue.txt")
    if not os.path.exists(j):
        return False
    lines = [l for l in io.open(j, encoding="utf-8") if l.strip()]
    return bool(lines) and lines[-1].startswith("RELU")


def pykey(p):
    out = []
    for part in p.split("/"):
        for syl in dk.syllables_of(part.strip()) or []:
            letters, tone = "", 5
            for ch in syl:
                base, t = dk.decode(ch)
                letters += base
                if t:
                    tone = t
            out.append(letters.lower() + str(tone))
    return "".join(out)


def main():
    write = "--ecrire" in sys.argv
    inv = read_tsv(os.path.join(HERE, "inventaire.tsv"))
    freq = {r["mot"]: int(r["rang"]) for r in read_tsv(os.path.join(HERE, "sources", "frequence.tsv"))}
    byid = OrderedDict((r["id"], r) for r in inv)

    # ---------- the sheets written and reviewed
    sheets, by_text, pending = {}, defaultdict(list), set()
    red = os.path.join(WORK, "rediges")
    for f in sorted(os.listdir(red)) if os.path.isdir(red) else []:
        if not f.endswith(".tsv"):
            continue
        lot = f[:-4]
        ok = reviewed(lot)
        for r in read_tsv(os.path.join(red, f)):
            if not ok:
                pending.add(r["id"])
                continue
            if lot.startswith("r"):
                sheets[r["id"]] = r
            else:
                by_text[(r["mot"], r["pinyin"])].append(r)
                sheets.setdefault("lot:" + r["id"], r)
    content = {}                                   # inventory id -> sheet
    twins = defaultdict(int)                       # homographs share their text: only their id finds their sheet
    for w in byid.values():
        twins[(w["mot"], w["pinyin"])] += 1
    for wid, w in byid.items():
        if w["etat"] == "existant":
            continue
        s = sheets.get("lot:" + wid)
        if not s and twins[(w["mot"], w["pinyin"])] == 1:
            c = by_text.get((w["mot"], w["pinyin"]), [])
            s = c[0] if len(c) == 1 else None
        if s:
            content[wid] = s

    # ---------- existing lists: corrections of the review, the split readings
    existing = {}
    for lid in ("hsk1", "hsk2", "hsk3"):
        existing[lid] = io.open(os.path.join(DECKS, lid + ".tsv"), encoding="utf-8").read()

    def fix_existing(lid, text):
        lines, count, head, out = text.split("\n"), defaultdict(int), None, []
        for line in lines:
            if not line.strip() or line.startswith("#"):
                out.append(line)
                continue
            cells = line.split("\t")
            if head is None:
                head = cells
                out.append(line)
                continue
            h = cells[0]
            count[h] += 1
            wid = "%s:%s%s" % (lid, h, "#%d" % count[h] if count[h] > 1 else "")
            new = dict(zip(head, cells + [""] * (len(head) - len(cells))))
            s = sheets.get(wid)
            if s:
                for k in FIELDS:
                    if k in head and s.get(k) is not None:
                        new[k] = s[k]
            new.update(SPLIT.get(wid, {}))
            row = [new.get(k, "") for k in head]
            while len(row) > 3 and not row[-1]:
                row.pop()
            out.append("\t".join(row))
        # the second readings and homographs, after the rows of the file (their ids: <list>:<hanzi>#2)
        for wid, w in byid.items():
            if w["etat"] in ("scission", "homographe") and w["maison"] == lid and wid in content:
                k = int(wid.split("#")[1]) if "#" in wid else 1
                if count[w["mot"]] >= k:         # already there
                    continue
                count[w["mot"]] += 1
                s = content[wid]
                row = [w["mot"], s["pinyin"]] + [s.get(k, "") for k in FIELDS[1:]]
                while len(row) > 3 and not row[-1]:
                    row.pop()
                while out and not out[-1].strip():
                    out.pop()
                out.append("\t".join(row))
                out.append("")
        return "\n".join(out)

    # ---------- which new lists can be written: every word with a reviewed sheet, in publication order
    members = defaultdict(list)
    for wid, w in byid.items():
        for l in w["listes"].split():
            members[l].append(wid)
    status, publish = OrderedDict(), []
    blocked = False
    for lid in ORDER[3:]:
        missing = [wid for wid in members[lid] if byid[wid]["etat"] != "existant" and wid not in content]
        status[lid] = (len(members[lid]), len(missing))
        if not missing and not blocked:
            publish.append(lid)
        else:
            blocked = True
    for lid, (n, m) in status.items():
        print("%-8s %-13s %4d mots, %s" % (lid, NAMES[lid], n, "complète" + (" : à publier" if lid in publish else " (attend les listes d'avant)") if not m else "%d sans fiche relue" % m))
    print("fiches relues : %d nouvelles, %d corrections de fiches existantes ; en attente de relecture : %d"
          % (len(content), sum(1 for k in sheets if not k.startswith("lot:")), len(pending)))
    if not write:
        return

    # ---------- pointers: characters, characters + pinyin, or the id
    words = [w for w in byid.values() if w["etat"] == "existant" or w["maison"] in publish or w["maison"] in ("hsk1", "hsk2", "hsk3")]
    by_h = defaultdict(list)
    for w in words:
        by_h[w["mot"]].append(w)

    def pointer(w, pinyin):
        same = by_h[w["mot"]]
        if len(same) == 1:
            return w["mot"]
        k = pykey(pinyin)
        if sum(1 for x in same if pykey(x["pinyin"] if x["etat"] == "existant" else (content.get(x["id"]) or x)["pinyin"]) == k) == 1:
            return w["mot"] + "\t" + pinyin
        return w["id"]

    for lid in ("hsk1", "hsk2", "hsk3"):
        text = fix_existing(lid, existing[lid])
        if text != existing[lid]:
            io.open(os.path.join(DECKS, lid + ".tsv"), "w", encoding="utf-8", newline="\n").write(text)
            print("decks/%s.tsv corrigé" % lid)
    for lid in publish:
        n20 = lid[3:] if not lid.startswith("hsk30") else None
        head = ["# 形音义 : liste %s (%s)" % (NAMES[lid], "HSK 2.0, liste officielle de 2012" if n20 else "HSK 3.0, programme d'examen 2026"),
                "# Liste HSK : l'appli ne la modifie pas (decks.json : fixe). Produite par outils/hsk/assembler.py.",
                "# Une ligne par mot. Une ligne avec une traduction définit le mot ; une ligne sans traduction renvoie à un",
                "# mot défini dans une autre liste (ses caractères, avec son pinyin s'il le faut, ou son identifiant).",
                "\t".join(COLS)]
        rows = []
        for wid in sorted(members[lid], key=lambda i: (freq.get(byid[i]["mot"], 10 ** 6), list(byid).index(i))):
            w = byid[wid]
            if w["maison"] == lid and w["etat"] != "existant":
                s = content[wid]
                row = [w["mot"], s["pinyin"]] + [s.get(k, "") for k in FIELDS[1:]]
                while len(row) > 3 and not row[-1]:
                    row.pop()
                rows.append("\t".join(c.replace("\t", " ") for c in row))
            else:
                p = w["pinyin"] if w["etat"] == "existant" else content[wid]["pinyin"]
                rows.append(pointer(w, p))
        io.open(os.path.join(DECKS, lid + ".tsv"), "w", encoding="utf-8", newline="\n").write("\n".join(head + rows) + "\n")
        print("decks/%s.tsv : %d lignes" % (lid, len(rows)))
    cfg_path = os.path.join(DECKS, "decks.json")
    cfg = json.load(io.open(cfg_path, encoding="utf-8"))
    have = {l["id"]: l for l in cfg["listes"]}
    for lid in ("hsk1", "hsk2", "hsk3"):
        if lid in have:
            have[lid]["nom"] = NAMES[lid]
            have[lid]["fixe"] = True
    for lid in [l for l in ["hsk4", "hsk5", "hsk6"] + ["hsk30-%d" % i for i in range(1, 7)] if l in publish]:
        if lid not in have:
            cfg["listes"].append({"id": lid, "nom": NAMES[lid], "fichier": lid + ".tsv", "actif": False, "afficher": False, "fixe": True})
    io.open(cfg_path, "w", encoding="utf-8", newline="\n").write(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    print("decks/decks.json : %d listes" % len(cfg["listes"]))


if __name__ == "__main__":
    main()
