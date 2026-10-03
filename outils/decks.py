#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Outils pour les listes de mots de 形音义 (dossier decks/).

  python3 outils/decks.py verifier
      Vérifie decks.json et chaque liste : colonnes, doublons, pinyin, phrases d'exemple.

  python3 outils/decks.py ajouter 打印 "imprimer" --exemple "我要打印这张照片。" --traduction "Je dois imprimer cette photo."
      Ajoute un mot à la fin d'une liste (perso par défaut, sinon --liste hsk3).
      Le pinyin du mot et celui de l'exemple sont calculés si pypinyin est installé ;
      sinon donne-les avec --pinyin da3yin4 et --exemple-pinyin "...".

  python3 outils/decks.py completer decks/perso.tsv
      Remplit les pinyin manquants (mot et exemple) et met les tons en chiffres sous forme d'accents.

  python3 outils/decks.py nouvelle-liste hsk30-3 "HSK 3.0 niveau 3"
      Crée decks/hsk30-3.tsv (avec l'en-tête) et l'ajoute à decks/decks.json.
      Options : --rappel 3 (liste de rappel, 3 mots par jour), --inactive, --fichier nom.tsv

Le pinyin automatique demande pypinyin :  python3 -m pip install pypinyin
Le pinyin calculé reste à relire, surtout pour les caractères à plusieurs lectures.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DECKS = os.path.join(ROOT, "decks")
sys.path.insert(0, HERE)

import pinyin_auto  # noqa: E402

COLUMNS = ["hanzi", "pinyin", "francais", "note", "audio", "exemple", "exemple_pinyin", "exemple_fr"]
HAN = re.compile(r"[㐀-鿿豈-﫿]")
TONED = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
LETTER = re.compile(r"[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ]+")
INTERJ = {"m", "n", "ng", "hm", "hng"}
HEADER = """# 形音义 : liste {name}
# Une ligne par mot, colonnes séparées par une tabulation. Les lignes qui commencent par # sont ignorées.
# hanzi : le mot en caractères (obligatoire, sert d'identifiant : le modifier crée un nouveau mot)
# pinyin : avec accents (túshūguǎn) ou chiffres (tu2shu1guan3) ; deux lectures : « zhǐ / zhī »
# francais : sens séparés par « ; »
# note, audio (texte lu par la voix si le mot seul se lit mal), exemple, exemple_pinyin, exemple_fr : facultatifs
# L'ordre des lignes est l'ordre d'arrivée des mots.
"""


def read_lines(path):
    try:
        with open(path, encoding="utf-8-sig") as fh:
            return [line.rstrip("\n").rstrip("\r") for line in fh]
    except UnicodeDecodeError:
        sys.exit("%s n'est pas enregistré en UTF-8 (Excel fait souvent ça) : rouvre-le dans un éditeur de texte "
                 "et enregistre-le en UTF-8." % os.path.relpath(path))


def load_set(name):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return set(fh.read().split()) if name.endswith("syllabes.txt") else set(fh.read().strip())


SYLLABLES = load_set("syllabes.txt")
HSK13 = load_set("caracteres_hsk1-3.txt")


def lexicon():
    return pinyin_auto.load_lexicon(os.path.join(HERE, "lexique_hsk.tsv"), os.path.join(HERE, "lexique_complements.tsv"))


# ---------------------------------------------------------------- pinyin

def decode(ch):
    low = ch.lower()
    k = TONED.find(low)
    if k >= 0:
        return "aeiouv"[k // 4], k % 4 + 1
    return ("v" if low == "ü" else low), 0


def split_run(run, strict=True):
    """Découpe une suite de lettres en syllabes (túshūguǎn -> tú shū guǎn) ; None si impossible."""
    dec = [decode(c) for c in run]
    base = "".join(d[0] for d in dec)
    n = len(base)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for size in range(1, 7):
            if i + size > n:
                break
            s = base[i:i + size]
            ok = s in SYLLABLES and s not in INTERJ
            if ok and strict and i > 0 and s[0] in "aoe":
                ok = False
            if not ok and s == "r" and i > 0 and i + size == n:
                ok = True
            if not ok and s in INTERJ and i == 0 and size == n:
                ok = True
            if ok and (best[i + size] is None or len(best[i]) + 1 < len(best[i + size])):
                best[i + size] = best[i] + [run[i:i + size]]
    if best[n] is None:
        return split_run(run, False) if strict else None
    return best[n]


def syllables_of(pinyin):
    """Liste des syllabes d'un pinyin à accents ou à chiffres ; None si une partie n'est pas du pinyin."""
    p = pinyin.replace("’", "'")
    if re.search(r"[a-zü:]\d", p, re.I):
        out = []
        for m in re.finditer(r"([A-Za-züÜv:]+?)([1-5])", p.replace("'", "")):
            base = m.group(1).lower().replace("u:", "v").replace("ü", "v")
            if base not in SYLLABLES and base != "r":
                return None
            out.append(m.group(0))
        rest = re.sub(r"[A-Za-züÜv:]+?[1-5]", "", p.replace("'", ""))
        if LETTER.search(rest):
            return None
        return out
    out = []
    for run in LETTER.findall(p):
        syl = split_run(run)
        if syl is None:
            return None
        out.extend(syl)
    return out


def to_marked(numeric):
    """'tu2shu1guan3' -> 'túshūguǎn' ; le pinyin déjà à accents est rendu tel quel."""
    if not re.search(r"[a-zü:]\d", numeric, re.I):
        return numeric
    parts = []
    for chunk in numeric.split("/"):
        out = ""
        for s in pinyin_auto.numeric_syllables(chunk.strip()):
            brk = s.startswith(" ")
            m = pinyin_auto.mark(s.strip())
            if s.strip().lower() == "r5" and out:
                out += "r"
                continue
            if brk and out:
                out += " "
            elif out and m[:1].lower() in "aeoāáǎàēéěèōóǒò":
                out += "'"
            out += m
        parts.append(out)
    return " / ".join(parts)


def need_pypinyin():
    if pinyin_auto.lazy_pinyin is None:
        sys.exit("Le pinyin automatique demande pypinyin : python3 -m pip install pypinyin\n"
                 "(ou donne le pinyin toi-même avec --pinyin / --exemple-pinyin).")


# ---------------------------------------------------------------- lists

def load_config():
    path = os.path.join(DECKS, "decks.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg):
    with open(os.path.join(DECKS, "decks.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


class Sheet:
    """Un fichier de liste : lignes d'origine gardées (commentaires compris), lignes de mots éditables."""

    def __init__(self, path):
        self.path = path
        self.lines = read_lines(path) if os.path.exists(path) else []
        self.header = None
        self.cols = COLUMNS
        self.rows = []  # (index in self.lines, cells)
        self.space_rows = set()  # lines whose tabs had been turned into spaces (rewritten with tabs on save)
        for i, line in enumerate(self.lines):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cells = line.split("\t")
            if len(cells) == 1 and re.search(r" {2,}", line.strip()):
                cells = re.split(r" {2,}", line.strip())
                self.lines[i] = "\t".join(cells)
                self.space_rows.add(i)
            if self.header is None:
                keys = [c.strip().lower() for c in cells]
                if "hanzi" in keys:
                    self.header, self.cols = i, keys
                    continue
                self.header = -1
            self.rows.append((i, cells))

    def get(self, cells, col):
        if col not in self.cols:
            return ""
        k = self.cols.index(col)
        return cells[k].strip() if k < len(cells) else ""

    def set(self, idx, col, value):
        i, cells = self.rows[idx]
        k = self.cols.index(col)
        cells = cells + [""] * (k + 1 - len(cells))
        cells[k] = value
        self.rows[idx] = (i, cells)
        self.lines[i] = "\t".join(cells)

    def append(self, values):
        if self.header is None:
            self.lines.append("\t".join(COLUMNS))
            self.header, self.cols = len(self.lines) - 1, COLUMNS
        cells = [values.get(c, "") for c in self.cols]
        while len(cells) > 3 and not cells[-1]:
            cells.pop()
        self.lines.append("\t".join(cells))

    def save(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(self.lines).rstrip("\n") + "\n")


# ---------------------------------------------------------------- verifier

def verifier(_args):
    problems = {"erreur": 0, "avertissement": 0, "info": 0}

    def report(where, level, msg):
        problems[level] += 1
        print("%s  %s : %s" % (where, level, msg))

    try:
        cfg = load_config()
    except FileNotFoundError:
        sys.exit("decks/decks.json introuvable (lance la commande depuis le dossier de l'appli).")
    except json.JSONDecodeError as e:
        sys.exit("decks/decks.json n'est pas du JSON valide : %s (ligne %d). Une virgule en trop ou en moins ?" % (e.msg, e.lineno))
    listes = cfg.get("listes")
    if not isinstance(listes, list):
        sys.exit("decks/decks.json : il faut une clé \"listes\" contenant un tableau [ … ].")
    ids, total, seen_files = set(), 0, set()
    for n, lst in enumerate(listes, 1):
        where = "decks.json, liste %d" % n
        if not isinstance(lst, dict) or not lst.get("id") or not lst.get("fichier"):
            report(where, "erreur", "chaque liste doit avoir au moins \"id\" et \"fichier\"")
            continue
        lid, fichier = str(lst["id"]), str(lst["fichier"])
        if lid in ids:
            report(where, "erreur", "l'identifiant « %s » est déjà pris (ce doublon sera ignoré par l'appli)" % lid)
        if lid == "tel":
            report(where, "erreur", "« tel » est réservé aux mots ajoutés sur le téléphone")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", lid):
            report(where, "avertissement", "identifiant « %s » : garde lettres, chiffres, - et _ (il sert à retrouver la progression)" % lid)
        ids.add(lid)
        if lst.get("mode", "apprendre") not in ("apprendre", "rappel"):
            report(where, "avertissement", "mode « %s » inconnu : « apprendre » ou « rappel » (l'appli prendra « apprendre »)" % lst.get("mode"))
        if "parJour" in lst and not (isinstance(lst["parJour"], int) and lst["parJour"] >= 0):
            report(where, "avertissement", "parJour doit être un nombre entier positif")
        if "actif" in lst and not isinstance(lst["actif"], bool):
            report(where, "avertissement", "actif doit valoir true ou false (sans guillemets)")
        path = os.path.join(DECKS, fichier)
        if not os.path.exists(path):
            report(where, "erreur", "fichier decks/%s introuvable" % fichier)
            continue
        if fichier in seen_files:
            continue
        seen_files.add(fichier)
        total += check_sheet(Sheet(path), "decks/" + fichier, report)
    print("\n%d listes, %d mots : %d erreur(s), %d avertissement(s), %d remarque(s)." % (
        len(seen_files), total, problems["erreur"], problems["avertissement"], problems["info"]))
    if problems["erreur"]:
        sys.exit(1)


def check_sheet(sheet, name, report):
    if sheet.header is None:
        return 0
    if sheet.header == -1:
        report(name, "avertissement", "pas de ligne d'en-tête (hanzi, pinyin, francais…) : l'appli suppose l'ordre standard des colonnes")
    seen = {}
    for idx, (i, cells) in enumerate(sheet.rows):
        where = "%s:%d" % (name, i + 1)
        h = sheet.get(cells, "hanzi")
        if i in sheet.space_rows:
            report(where, "avertissement", "colonnes séparées par des espaces au lieu de tabulations (l'appli s'en accommode ; "
                   "python3 outils/decks.py completer %s remet des tabulations)" % name)
        if not h:
            report(where, "erreur", "la colonne hanzi est vide : la ligne est ignorée")
            continue
        where += "  " + h
        if len(cells) > len(sheet.cols):
            report(where, "avertissement", "%d colonnes pour %d attendues : une tabulation de trop ?" % (len(cells), len(sheet.cols)))
        if h in seen:
            report(where, "info", "« %s » apparaît aussi ligne %d : ce sera une carte distincte (normal si le sens diffère)" % (h, seen[h]))
        seen.setdefault(h, i + 1)
        p, f = sheet.get(cells, "pinyin"), sheet.get(cells, "francais")
        nhan = len(HAN.findall(h))
        if not p:
            report(where, "avertissement", "pas de pinyin (python3 outils/decks.py completer %s le calcule)" % name)
        else:
            for alt in p.split("/"):
                syl = syllables_of(alt.strip())
                if syl is None:
                    report(where, "avertissement", "pinyin « %s » : une partie n'est pas une syllabe connue" % alt.strip())
                elif nhan and len(syl) != nhan:
                    hint = " (apostrophe oubliée, comme dans xī'ān ?)" if len(syl) < nhan else ""
                    report(where, "avertissement", "pinyin « %s » : %d syllabe(s) pour %d caractère(s)%s" % (alt.strip(), len(syl), nhan, hint))
        if not f:
            report(where, "avertissement", "pas de traduction française")
        e, ep = sheet.get(cells, "exemple"), sheet.get(cells, "exemple_pinyin")
        if e:
            if h not in e:
                report(where, "avertissement", "l'exemple ne contient pas le mot")
            if HSK13:
                outside = sorted({c for c in HAN.findall(e) if c not in HSK13})
                if outside:
                    report(where, "info", "exemple : caractères hors HSK 1-3 : %s" % " ".join(outside))
            if not ep:
                report(where, "info", "exemple sans pinyin (python3 outils/decks.py completer %s le calcule)" % name)
            elif syllables_of(ep) is None:
                report(where, "avertissement", "pinyin de l'exemple : une partie n'est pas une syllabe connue")
        elif ep or sheet.get(cells, "exemple_fr"):
            report(where, "avertissement", "pinyin ou traduction d'exemple sans phrase d'exemple")
    return len(sheet.rows)


# ---------------------------------------------------------------- ajouter / completer / nouvelle-liste

def find_list(cfg, lid):
    for lst in cfg.get("listes", []):
        if str(lst.get("id")) == lid:
            return lst
    sys.exit("Pas de liste « %s » dans decks/decks.json. Listes : %s" % (lid, ", ".join(str(l.get("id")) for l in cfg.get("listes", []))))


def ajouter(args):
    cfg = load_config()
    lst = find_list(cfg, args.liste)
    path = os.path.join(DECKS, lst["fichier"])
    sheet = Sheet(path)
    h = args.hanzi.strip()
    if not HAN.search(h):
        sys.exit("« %s » ne contient pas de caractère chinois." % h)
    if any(sheet.get(c, "hanzi") == h for _, c in sheet.rows) and not args.force:
        sys.exit("« %s » est déjà dans %s (ajoute --force pour une deuxième carte, avec un autre sens)." % (h, lst["fichier"]))
    for other in cfg.get("listes", []):
        if other is lst or not os.path.exists(os.path.join(DECKS, other["fichier"])):
            continue
        o = Sheet(os.path.join(DECKS, other["fichier"]))
        if any(o.get(c, "hanzi") == h for _, c in o.rows):
            print("Remarque : « %s » est aussi dans la liste %s." % (h, other.get("nom", other["id"])))
    lex = None
    auto = False
    if args.pinyin:
        p = to_marked(args.pinyin.strip())
    else:
        need_pypinyin()
        lex = lexicon()
        p = pinyin_auto.word_pinyin(h, lex)
        auto = True
    ex = (args.exemple or "").strip()
    ep = (args.exemple_pinyin or "").strip()
    if ex and not ep:
        if pinyin_auto.lazy_pinyin is None:
            print("Remarque : sans pypinyin, le pinyin de l'exemple reste vide.")
        else:
            ep = pinyin_auto.sentence_pinyin(ex, lex or lexicon())
            auto = True
    values = {"hanzi": h, "pinyin": p, "francais": args.francais.strip(), "note": (args.note or "").strip(),
              "audio": (args.audio or "").strip(), "exemple": ex, "exemple_pinyin": ep, "exemple_fr": (args.traduction or "").strip()}
    for k, v in values.items():
        if "\t" in v or "\n" in v:
            sys.exit("Le champ %s contient une tabulation ou un retour à la ligne." % k)
    sheet.append(values)
    sheet.save()
    print("Ajouté à decks/%s :" % lst["fichier"])
    print("  %s  %s  %s" % (h, p, values["francais"]))
    if ex:
        print("  例 %s\n     %s\n     %s" % (ex, ep or "(pinyin à ajouter)", values["exemple_fr"] or "(traduction à ajouter)"))
        if h not in ex:
            print("Attention : la phrase ne contient pas « %s »." % h)
    if auto:
        print("Pinyin calculé automatiquement : relis-le avant de publier.")
    print("Pour l'envoyer sur le téléphone :  git add decks && git commit -m \"Ajoute %s\" && git push" % h)


def completer(args):
    path = args.fichier
    if not os.path.exists(path):
        alt = os.path.join(DECKS, os.path.basename(path))
        if os.path.exists(alt):
            path = alt
        else:
            sys.exit("Fichier introuvable : %s" % args.fichier)
    sheet = Sheet(path)
    lex = None
    changes = len(sheet.space_rows)
    for i in sorted(sheet.space_rows):
        print("ligne %d  espaces remplacés par des tabulations" % (i + 1))
    for idx, (i, cells) in enumerate(list(sheet.rows)):
        h = sheet.get(cells, "hanzi")
        if not h:
            continue
        p = sheet.get(cells, "pinyin")
        new_p = p
        if not p:
            need_pypinyin()
            lex = lex or lexicon()
            new_p = pinyin_auto.word_pinyin(h, lex)
        elif re.search(r"[a-zü:]\d", p, re.I):
            new_p = to_marked(p)
        if new_p != p and "pinyin" in sheet.cols:
            sheet.set(idx, "pinyin", new_p)
            print("ligne %d  %s  pinyin : %s" % (i + 1, h, new_p))
            changes += 1
        cells = sheet.rows[idx][1]
        e, ep = sheet.get(cells, "exemple"), sheet.get(cells, "exemple_pinyin")
        if e and not ep and "exemple_pinyin" in sheet.cols:
            need_pypinyin()
            lex = lex or lexicon()
            ep = pinyin_auto.sentence_pinyin(e, lex)
            sheet.set(idx, "exemple_pinyin", ep)
            print("ligne %d  %s  exemple : %s" % (i + 1, h, ep))
            changes += 1
    if changes:
        sheet.save()
        print("\n%d champ(s) rempli(s) dans %s. Relis le pinyin calculé, puis publie avec git." % (changes, os.path.relpath(path)))
    else:
        print("Rien à compléter dans %s." % os.path.relpath(path))


def nouvelle_liste(args):
    cfg = load_config()
    lid = args.id.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", lid) or lid == "tel":
        sys.exit("Identifiant « %s » : utilise lettres, chiffres, - et _ (et pas « tel »)." % lid)
    if any(str(l.get("id")) == lid for l in cfg.get("listes", [])):
        sys.exit("La liste « %s » existe déjà dans decks.json." % lid)
    fichier = args.fichier or lid + ".tsv"
    path = os.path.join(DECKS, fichier)
    if os.path.exists(path):
        print("decks/%s existe déjà : il est gardé tel quel." % fichier)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(HEADER.format(name=args.nom) + "\t".join(COLUMNS) + "\n")
        print("Créé : decks/%s" % fichier)
    entry = {"id": lid, "nom": args.nom, "fichier": fichier, "mode": "rappel" if args.rappel else "apprendre"}
    if args.rappel:
        entry["parJour"] = args.rappel
    entry["actif"] = not args.inactive
    cfg.setdefault("listes", []).append(entry)
    save_config(cfg)
    print("Ajoutée à decks/decks.json, en dernière position (l'ordre des listes est l'ordre de priorité des nouveaux mots).")
    print("Remplis le fichier, vérifie avec  python3 outils/decks.py verifier  puis publie avec git.")


def main():
    ap = argparse.ArgumentParser(prog="decks.py", description="Outils pour les listes de mots de 形音义 (dossier decks/).",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verifier", help="vérifie decks.json et toutes les listes").set_defaults(func=verifier)
    a = sub.add_parser("ajouter", help="ajoute un mot à une liste")
    a.add_argument("hanzi")
    a.add_argument("francais")
    a.add_argument("--liste", default="perso", help="identifiant de la liste (perso par défaut)")
    a.add_argument("--pinyin", help="pinyin du mot (accents ou chiffres) ; calculé sinon")
    a.add_argument("--note")
    a.add_argument("--audio", help="texte lu par la voix si le mot seul se lit mal")
    a.add_argument("--exemple", help="phrase d'exemple en caractères (contenant le mot)")
    a.add_argument("--exemple-pinyin", dest="exemple_pinyin", help="pinyin de la phrase ; calculé sinon")
    a.add_argument("--traduction", help="traduction française de la phrase")
    a.add_argument("--force", action="store_true", help="accepte un deuxième mot identique dans la même liste")
    a.set_defaults(func=ajouter)
    c = sub.add_parser("completer", help="remplit les pinyin manquants d'un fichier")
    c.add_argument("fichier")
    c.set_defaults(func=completer)
    n = sub.add_parser("nouvelle-liste", help="crée une liste vide et l'inscrit dans decks.json")
    n.add_argument("id")
    n.add_argument("nom")
    n.add_argument("--fichier")
    n.add_argument("--rappel", type=int, metavar="N", help="liste de rappel, N mots par jour")
    n.add_argument("--inactive", action="store_true", help="inscrite mais désactivée")
    n.set_defaults(func=nouvelle_liste)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
