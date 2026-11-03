# -*- coding: utf-8 -*-
"""Exercices au format du HSK 3 (2.0), sans les images : exos/hsk3.json, lu par l'appli (onglet HSK).

    py outils\\exos.py verifier              contrôle exos/hsk3.json
    py outils\\exos.py ajouter <lot.txt>     ajoute les questions d'un lot rédigé (format ci-dessous), avec leur pinyin
    py outils\\exos.py completer             remplit le pinyin qui manque (après une correction à la main)

ajouter et completer demandent pypinyin (py -m pip install pypinyin).

Parties : e2, e3, e4 (听力 2, 3 et 4 : vrai ou faux, dialogue court, dialogue long), l1, l2, l3 (阅读 1, 2 et 3 :
phrases qui vont ensemble, mot à placer, petit texte), w1 (书写 1 : ordre des mots). 书写 2 (caractère d'après le pinyin)
est tiré par l'appli des phrases d'exemple des listes HSK 1 à 3.

Format d'un lot : une ligne « ## e3 » (la partie) avant ses questions, une question par bloc, les blocs séparés par une
ligne vide, chaque texte suivi de « | » et de sa traduction ; les lignes qui commencent par « # » sont ignorées.

    ## e2                                   (une phrase entendue, une phrase écrite : vrai ou faux)
    男：我每天早上七点起床，然后去公园跑步。 | Je me lève à 7 h tous les matins, puis je vais courir au parc.
    ★ 他每天早上去跑步。 | Il va courir tous les matins.
    = vrai

    ## e3 (deux répliques) ou e4 (quatre ou cinq)
    女：你明天几点去机场？ | À quelle heure vas-tu à l’aéroport demain ?
    男：早上八点，飞机十点起飞。 | À 8 h, l’avion décolle à 10 h.
    问：飞机几点起飞？ | À quelle heure l’avion décolle-t-il ?
    A 八点 | 8 h
    B 十点 | 10 h
    C 十二点 | midi
    = B

    ## l1                                   (cinq paires : la phrase, puis la réponse qui va avec)
    你怎么还没睡觉？ | Pourquoi tu ne dors pas ? => 明天有考试，我想再看看书。 | J’ai un examen demain, je révise encore.

    ## l2                                   (six mots, cinq phrases ; la réponse entre parenthèses ; un dialogue : « // »)
    mots : 同意 关心 声音 简单 一般 终于
    我（同意）你的看法。 | Je suis d’accord avec toi.
    A：你的感冒好了吗？ // B：好多了，谢谢你的（关心）。 | A : Ton rhume va mieux ? // B : Beaucoup mieux, merci de t’en soucier.

    ## l3                                   (un texte, une question, trois réponses)
    ...texte... | ...traduction...
    ★ 他为什么…？ | Pourquoi… ?
    A … | …
    B … | …
    C … | …
    = A

    ## w1                                   (les blocs dans le bon ordre, la ponctuation à la fin ; « ou » : un autre ordre juste)
    那家 / 宾馆 / 离机场 / 很远。 | Cet hôtel est loin de l’aéroport.
    ou …。

Contrôles : caractères du HSK 1 à 3 seulement (outils/caracteres_hsk1-3.txt, plus le nom de famille 王), structure de
chaque partie, réponse unique et valide, blocs qui redonnent la phrase, pinyin et traduction présents.
Sortie : une ligne par problème ; code 1 s'il y en a.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FILE = os.path.join(REPO, "exos", "hsk3.json")
sys.path.insert(0, HERE)
import pinyin_auto  # noqa: E402

PARTS = ["e2", "e3", "e4", "l1", "l2", "l3", "w1"]
HAN = re.compile(r"[㐀-鿿]")
END = "。？！"
EXTRA = set("王")                                   # 小王, 王老师 : le nom de famille des sujets du HSK
LABEL = re.compile(r"^(男|女|A|B)：")


def hsk_chars():
    return set(io.open(os.path.join(HERE, "caracteres_hsk1-3.txt"), encoding="utf-8").read().strip()) | EXTRA


def lexicon():
    return pinyin_auto.load_lexicon(os.path.join(HERE, "lexique_hsk.tsv"), os.path.join(HERE, "lexique_complements.tsv"))


def load():
    if not os.path.exists(FILE):
        return {"v": 1, **{k: [] for k in PARTS}}
    data = json.load(io.open(FILE, encoding="utf-8"))
    for k in PARTS:
        data.setdefault(k, [])
    return data


def dump(data):
    # one question per line: a change shows as one line in git
    out = ['{"v": %d,' % data.get("v", 1)]
    for n, k in enumerate(PARTS):
        rows = ["  " + json.dumps(it, ensure_ascii=False, separators=(",", ":")) for it in data.get(k, [])]
        out.append(' "%s": [' % k + ("\n" + ",\n".join(rows) + "\n " if rows else "") + "]" + ("," if n < len(PARTS) - 1 else ""))
    out.append("}")
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    io.open(FILE, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")


# ---------- texts: {zh, py, fr} ----------
def texts(it):
    """Every text of a question: (where, dict with zh)."""
    for k, v in it.items():
        if isinstance(v, dict) and "zh" in v:
            yield k, v
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, dict) and "zh" in x:
                    yield "%s[%d]" % (k, i), x
                elif isinstance(x, dict):
                    for kk, y in x.items():
                        if isinstance(y, dict) and "zh" in y:
                            yield "%s[%d].%s" % (k, i, kk), y
    if "zh" in it and isinstance(it["zh"], str):
        yield "phrase", it


def pinyin_of(zh, lex):
    # each line on its own, without its speaker (A：, 男：)
    return "\n".join(pinyin_auto.sentence_pinyin(LABEL.sub("", line), lex) for line in zh.split("\n"))


def fill_pinyin(it, lex, force=False):
    n = 0
    for _, t in texts(it):
        if force or not t.get("py"):
            t["py"] = pinyin_of(t["zh"], lex)
            n += 1
    return n


# ---------- reading a batch ----------
def split_text(line, where):
    if " | " not in line:
        raise ValueError("%s : « | traduction » manque : %s" % (where, line))
    zh, fr = line.split(" | ", 1)
    return {"zh": zh.strip(), "fr": fr.strip()}


def parse_choice(lines, where):
    opts, ans = [], None
    for line in lines:
        m = re.match(r"^([ABC]) (.+)$", line)
        if m:
            opts.append(split_text(m.group(2), where))
        elif line.startswith("="):
            ans = "ABC".index(line[1:].strip())
    if len(opts) != 3 or ans is None:
        raise ValueError("%s : il faut trois réponses A, B, C et « = » la bonne" % where)
    return opts, ans


def parse_block(part, lines, where):
    if part == "e2":
        t = split_text(lines[0], where)
        s = None
        m = re.match(r"^(男|女)：", t["zh"])
        if m:
            s = m.group(1)
            t["zh"] = t["zh"][2:]
            t["fr"] = re.sub(r"^(Homme|Femme) ?: ?", "", t["fr"])
        q = split_text(lines[1].lstrip("★ ").strip(), where)
        v = lines[2].lstrip("= ").strip()
        if v not in ("vrai", "faux"):
            raise ValueError("%s : « = vrai » ou « = faux »" % where)
        it = {"t": t, "q": q, "ok": v == "vrai"}
        if s:
            it["s"] = s
        return it
    if part in ("e3", "e4"):
        dia, q, rest = [], None, []
        for line in lines:
            m = re.match(r"^(男|女)：(.+)$", line)
            if m and q is None:
                t = split_text(m.group(2), where)
                dia.append({"s": m.group(1), **t})
            elif line.startswith("问："):
                q = split_text(line[2:], where)
            else:
                rest.append(line)
        opts, ans = parse_choice(rest, where)
        return {"dia": dia, "q": q, "opts": opts, "ans": ans}
    if part == "l1":
        pairs = []
        for line in lines:
            if " => " not in line:
                raise ValueError("%s : « => » entre la phrase et sa réponse" % where)
            a, b = line.split(" => ", 1)
            pairs.append({"a": split_text(a, where), "b": split_text(b, where)})
        return {"pairs": pairs}
    if part == "l2":
        head = lines[0]
        if not head.startswith("mots"):
            raise ValueError("%s : la première ligne donne les six mots (mots : …)" % where)
        mots = head.split(":", 1)[1].split() if ":" in head else head.split("：", 1)[1].split()
        items = []
        for line in lines[1:]:
            t = split_text(line, where)
            zh = t["zh"].replace(" // ", "\n").replace("//", "\n")
            m = re.search(r"（([^（）]+)）", zh)
            if not m:
                raise ValueError("%s : la réponse entre （ ） manque : %s" % (where, zh))
            items.append({"zh": zh[:m.start()] + m.group(1) + zh[m.end():], "at": m.start(), "mot": m.group(1),
                          "fr": t["fr"].replace(" // ", "\n").replace("//", "\n")})
        return {"mots": mots, "items": items}
    if part == "l3":
        txt = split_text(lines[0], where)
        q = split_text(lines[1].lstrip("★ ").strip(), where)
        opts, ans = parse_choice(lines[2:], where)
        return {"txt": txt, "q": q, "opts": opts, "ans": ans}
    if part == "w1":
        t = split_text(lines[0], where)
        blocs = [b.strip() for b in t["zh"].split("/")]
        end = blocs[-1][-1] if blocs[-1] and blocs[-1][-1] in END else "。"
        blocs[-1] = blocs[-1].rstrip(END)
        it = {"blocs": blocs, "zh": "".join(blocs) + end, "fr": t["fr"]}
        alt = [line[2:].strip() for line in lines[1:] if line.startswith("ou ")]
        if alt:
            it["alt"] = alt
        return it
    raise ValueError("partie inconnue : %s" % part)


def read_batch(path):
    part, blocks, cur, start = None, [], [], 0
    for n, raw in enumerate(io.open(path, encoding="utf-8-sig"), 1):
        line = raw.strip()
        if line.startswith("##"):
            if cur:
                blocks.append((part, cur, start))
                cur = []
            part = line[2:].split()[0].strip()
            if part not in PARTS:
                raise ValueError("ligne %d : partie inconnue « %s » (%s)" % (n, part, " ".join(PARTS)))
            continue
        if line.startswith("#"):
            continue
        if not line:
            if cur:
                blocks.append((part, cur, start))
                cur = []
            continue
        if part is None:
            raise ValueError("ligne %d : « ## partie » manque avant la première question" % n)
        if not cur:
            start = n
        cur.append(line)
    if cur:
        blocks.append((part, cur, start))
    return [(part, parse_block(part, lines, "%s, ligne %d" % (os.path.basename(path), start))) for part, lines, start in blocks]


def next_id(data, part):
    nums = [int(it["id"].split("-")[1]) for it in data[part] if re.match(r"^[a-z]\d-\d+$", it.get("id", ""))]
    return "%s-%03d" % (part, max(nums, default=0) + 1)


# ---------- checks ----------
def problems(data):
    chars, out = hsk_chars(), []
    seen_ids = set()

    def bad(it, msg):
        out.append("%s : %s" % (it.get("id", "?"), msg))

    for part in PARTS:
        for it in data.get(part, []):
            iid = it.get("id")
            if not iid or iid in seen_ids or not iid.startswith(part + "-"):
                bad(it, "identifiant manquant, en double ou d'une autre partie")
            seen_ids.add(iid)
            for where, t in texts(it):
                zh = t.get("zh", "")
                odd = sorted({c for c in zh if HAN.match(c) and c not in chars})
                if odd:
                    bad(it, "%s : caractères hors du HSK 1-3 : %s" % (where, "".join(odd)))
                if not t.get("fr"):
                    bad(it, "%s : traduction manquante" % where)
                if not t.get("py"):
                    bad(it, "%s : pinyin manquant (py outils\\exos.py completer)" % where)
                elif t["py"].count("\n") != zh.count("\n"):
                    bad(it, "%s : pinyin et caractères n'ont pas le même nombre de lignes" % where)
            if part == "e2":
                if not isinstance(it.get("ok"), bool) or it.get("s") not in (None, "男", "女"):
                    bad(it, "« ok » (vrai ou faux) ou « s » (男, 女) invalide")
            if part in ("e3", "e4", "l3"):
                opts = it.get("opts", [])
                if len(opts) != 3 or len({o.get("zh") for o in opts}) != 3:
                    bad(it, "il faut trois réponses différentes")
                if it.get("ans") not in (0, 1, 2):
                    bad(it, "« ans » doit valoir 0, 1 ou 2")
                if part != "l3":
                    dia = it.get("dia", [])
                    n_ok = len(dia) == 2 if part == "e3" else 4 <= len(dia) <= 6
                    if not n_ok:
                        bad(it, "dialogue de %d répliques (%s)" % (len(dia), "2" if part == "e3" else "4 à 6"))
                    if any(a.get("s") == b.get("s") for a, b in zip(dia, dia[1:])) or any(d.get("s") not in ("男", "女") for d in dia):
                        bad(it, "les répliques doivent alterner 男 et 女")
                    if not it.get("q"):
                        bad(it, "question manquante")
            if part == "l1":
                pairs = it.get("pairs", [])
                if len(pairs) != 5 or len({p["a"]["zh"] for p in pairs}) != 5 or len({p["b"]["zh"] for p in pairs}) != 5:
                    bad(it, "il faut cinq paires, toutes différentes")
            if part == "l2":
                mots, items = it.get("mots", []), it.get("items", [])
                if len(mots) != 6 or len(set(mots)) != 6:
                    bad(it, "il faut six mots différents")
                if len(items) != 5 or len({x.get("mot") for x in items}) != 5:
                    bad(it, "il faut cinq phrases, chacune avec un autre mot")
                for x in items:
                    if x.get("mot") not in mots:
                        bad(it, "« %s » n'est pas dans les mots" % x.get("mot"))
                    if x.get("zh", "")[x.get("at", -1):x.get("at", -1) + len(x.get("mot", ""))] != x.get("mot"):
                        bad(it, "position du mot (at) fausse dans « %s »" % x.get("zh"))
            if part == "w1":
                blocs, zh = it.get("blocs", []), it.get("zh", "")
                if not 3 <= len(blocs) <= 6 or any(not b for b in blocs):
                    bad(it, "il faut de trois à six blocs")
                if "".join(blocs) != zh.rstrip(END) or not zh or zh[-1] not in END:
                    bad(it, "les blocs ne redonnent pas la phrase « %s »" % zh)
                for a in it.get("alt", []):
                    if not can_build(a.rstrip(END), blocs):
                        bad(it, "« %s » n'est pas fait des mêmes blocs" % a)
                if len(set(blocs)) != len(blocs):
                    bad(it, "deux blocs identiques")
    return out


def can_build(s, blocs):
    if not blocs:
        return not s
    return any(s.startswith(b) and can_build(s[len(b):], blocs[:i] + blocs[i + 1:]) for i, b in enumerate(blocs))


def cmd_verifier():
    data = load()
    out = problems(data)
    for line in out:
        print(line)
    counts = ", ".join("%s %d" % (k, len(data[k])) for k in PARTS)
    print("%s : %s ; %s" % (os.path.relpath(FILE, REPO), counts, "aucun problème" if not out else "%d problème(s)" % len(out)))
    return 1 if out else 0


def cmd_ajouter(path):
    data, lex = load(), lexicon()
    batch = read_batch(path)
    for part, it in batch:
        it = {"id": next_id(data, part), **it}
        fill_pinyin(it, lex)
        data[part].append(it)
    out = problems(data)
    for line in out:
        print(line)
    if out:
        print("rien n'est écrit : corrige le lot, puis relance")
        return 1
    dump(data)
    print("%d question(s) ajoutée(s) à %s" % (len(batch), os.path.relpath(FILE, REPO)))
    return 0


def cmd_completer():
    data, lex = load(), lexicon()
    n = sum(fill_pinyin(it, lex) for k in PARTS for it in data[k])
    dump(data)
    print("pinyin rempli : %d texte(s)" % n)
    return cmd_verifier()


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["verifier"]:
        sys.exit(cmd_verifier())
    if args[:1] == ["ajouter"] and len(args) == 2:
        sys.exit(cmd_ajouter(args[1]))
    if args[:1] == ["completer"]:
        sys.exit(cmd_completer())
    print(__doc__)
    sys.exit(2)
