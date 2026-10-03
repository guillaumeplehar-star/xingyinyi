# -*- coding: utf-8 -*-
"""Pinyin automatique pour les listes de 形音义 (mots et phrases d'exemple).

Nécessite pypinyin :  pip install pypinyin

pypinyin choisit déjà la bonne lecture des caractères à plusieurs prononciations
d'après les mots voisins (还给 huán gěi, 还有 hái yǒu). Ce module ajoute les
conventions des manuels :
  - le 一 et le 不 notés avec leur ton réel (yí ge, yì qǐ, bú shì) ;
  - les particules au ton neutre (的 de, 地 de, 得 de, 了 le, 着 zhe, 过 guo) ;
  - le 儿 collé au mot (zhèr, diǎnr) ;
  - les tons neutres des mots HSK repris des listes officielles (péngyou, dìfang) ;
  - une majuscule en début de phrase et pour quelques noms propres.
Le résultat reste à relire pour les phrases inhabituelles.
"""
import os
import re

try:
    from pypinyin import lazy_pinyin, Style
    from pypinyin.constants import PHRASES_DICT
except ImportError:  # the checker works without pypinyin
    lazy_pinyin = Style = None
    PHRASES_DICT = {}

HAN = re.compile(r"[㐀-鿿]")
MARKS = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}
PUNCT = {"。": ".", "，": ",", "？": "?", "！": "!", "：": ":", "；": ";", "、": ",",
         "“": "« ", "”": " »", "（": "(", "）": ")", "—": "–"}
NUMERALS = set("一二三四五六七八九十两几百千万零")
CLASSIFIERS = set("个本只杯件条张双块次位辆把节道口岁点课号月层碗")
VERBS_GUO = set("去来看住吃听学做说见到用玩坐骑买想试喝打写读找")
VERBS_BU = set("听看找吃做说写拿买走跑记想睡用打学")
COMPLEMENTS_BU = set("清到见完懂了起动好会出开下")
DIRECTIONAL = set("起上下出进回过")
REDUP = set("看走想试说听等问坐玩谈")
PROPER = {"法国": "Fǎguó", "春节": "Chūnjié", "小明": "Xiǎomíng", "小白": "Xiǎobái",
          "北京大学": "Běijīng Dàxué", "黄河": "Huánghé"}


def mark(syl):
    """'hao3' -> 'hǎo', 'lv4' -> 'lǜ', 'de5' -> 'de'."""
    m = re.fullmatch(r"([A-Za-züÜv:]+)([1-5]?)", syl)
    if not m:
        return syl
    s, tone = m.group(1), int(m.group(2) or 5)
    s = s.replace("u:", "ü").replace("v", "ü").replace("U:", "Ü").replace("V", "Ü")
    if tone == 5:
        return s
    low = s.lower()
    k = low.find("a")
    if k < 0:
        k = low.find("e")
    if k < 0 and "ou" in low:
        k = low.find("o")
    if k < 0:
        for i in range(len(low) - 1, -1, -1):
            if low[i] in "iouü":
                k = i
                break
    if k < 0:
        return s
    ch = MARKS[low[k]][tone - 1]
    if s[k] != low[k]:
        ch = ch.upper()
    return s[:k] + ch + s[k + 1:]


def numeric_syllables(numeric):
    """'tu2shu1guan3' -> ['tu2', 'shu1', 'guan3'] ; 'yi2hui4r5' -> [..., 'r5'].
    A syllable that follows a space in the source keeps a leading space ('bu2 ke4qi5')."""
    return [m.group(1) + m.group(2) for m in re.finditer(r"(\s?)([A-Za-züÜv:]+?[1-5])", numeric.replace("'", ""))]


def load_lexicon(*paths):
    """Fichiers 'mot<TAB>pinyin numérique' (lignes # ignorées)."""
    lex = {}
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2 or "," in parts[1]:
                    continue
                word, syls = parts[0], numeric_syllables(parts[1])
                if len(syls) == len(word):
                    lex[word] = syls
    return lex


def segment(text, lex):
    """Découpage en mots d'après le lexique (plus long mot d'abord). Les nombres
    composés restent groupés (èrshí), un nombre suivi d'un classificateur non."""
    words, i = [], 0
    while i < len(text):
        c = text[i]
        if c == "—":
            j = i
            while j < len(text) and text[j] == "—":
                j += 1
            words.append("——")
            i = j
            continue
        if not HAN.match(c):
            words.append(c)
            i += 1
            continue
        if c in NUMERALS and c not in "几两":
            j = i
            while j < len(text) and text[j] in NUMERALS and text[j] not in "几两":
                j += 1
            run = text[i:j]
            if j < len(text) and text[j] == "月":  # 一月, 十月 : yīyuè, shíyuè
                words.append(run + "月")
                i = j + 1
                continue
            if len(run) > 1 and any(x in run for x in "十百千万"):
                words.append(run)
                i = j
                continue
        found = None
        after_number = bool(words) and (words[-1][-1:] in NUMERALS or words[-1] in ("这", "那", "哪", "每"))
        if not (c in CLASSIFIERS and after_number):  # 六个人 : liù ge rén, pas gèrén
            for size in (4, 3, 2):
                piece = text[i:i + size]
                if len(piece) == size and piece in lex:
                    found = piece
                    break
        found = found or c
        words.append(found)
        i += len(found)
    return words


def tone_of(syl):
    m = re.search(r"([1-5])$", syl.strip())
    return int(m.group(1)) if m else 5


def sentence_pinyin(text, lex):
    """Phrase en caractères -> pinyin à accents, mots séparés par des espaces."""
    if lazy_pinyin is None:
        raise RuntimeError("pypinyin manque : pip install pypinyin")
    chars = list(text)
    base = lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True, errors=lambda s: list(s))
    assert len(base) == len(chars), (text, base)
    syl = [b if HAN.match(c) else None for b, c in zip(base, chars)]
    fixed = [False] * len(chars)
    words = segment(text, lex)
    pos = 0
    spans = []
    for w in words:
        spans.append((pos, pos + len(w)))
        if w in lex and len(w) > 1 and all(HAN.match(c) for c in w):
            for k, s in enumerate(lex[w]):
                syl[pos + k] = s
                fixed[pos + k] = True
        elif w == "谁":
            syl[pos] = "shei2"
        pos += len(w)

    def word_of(i):
        for a, b in spans:
            if a <= i < b:
                return text[a:b]
        return text[i]

    n = len(chars)
    for i, c in enumerate(chars):
        if syl[i] is None or fixed[i]:
            continue
        prev = chars[i - 1] if i > 0 else ""
        nxt = chars[i + 1] if i + 1 < n else ""
        single = len(word_of(i)) == 1
        if c == "的":
            syl[i] = "de5"
        elif c == "地" and single:
            syl[i] = "de5"
        elif c == "得" and single:
            syl[i] = "de5"
        elif c == "了" and single:
            syl[i] = "le5"
        elif c == "着" and single:
            syl[i] = "zhe5"
        elif c == "个":
            syl[i] = "ge5"
        elif c == "只" and single and (prev in NUMERALS or prev in "这那哪每"):
            syl[i] = "zhi1"
        elif c == "长" and single:
            syl[i] = "zhang3" if nxt in "得大" else "chang2"
        elif c == "教" and single:
            syl[i] = "jiao1"
        elif c == "吧" and single:
            syl[i] = "ba5"
        elif c == "李" and single:
            syl[i] = "Li3"
        elif c == "过" and single:
            syl[i] = "guo5" if prev in VERBS_GUO else "guo4"
        elif c in "来去" and prev in DIRECTIONAL and i >= 1 and not fixed[i - 1]:
            syl[i] = syl[i][:-1] + "5"
        elif c == "儿" and word_of(i) not in ("儿子", "女儿"):
            syl[i] = "r5"
        elif c == prev and c in REDUP and single:
            syl[i] = syl[i][:-1] + "5"

    for i, c in enumerate(chars):
        if fixed[i] or syl[i] is None:
            continue
        prev = chars[i - 1] if i > 0 else ""
        nxt = chars[i + 1] if i + 1 < n else ""
        nxt_tone = tone_of(syl[i + 1]) if i + 1 < n and syl[i + 1] else None
        if c == "一":
            if prev == "第" or nxt in "月号日" or prev in NUMERALS or nxt_tone is None:
                syl[i] = "yi1"
            elif nxt == "个" or nxt_tone == 4:
                syl[i] = "yi2"
            else:
                syl[i] = "yi4"
        elif c == "不":
            if prev in VERBS_BU and nxt in COMPLEMENTS_BU:
                syl[i] = "bu5"
            elif nxt_tone == 4:
                syl[i] = "bu2"
            else:
                syl[i] = "bu4"

    out = []
    pos = 0
    for w in words:
        if w == "——":
            out.append("–")
            pos += len(w)
            continue
        if not HAN.match(w[0]):
            p = PUNCT.get(w, w)
            if p in ".,?!:;)»" or p.startswith(" "):
                if out:
                    out[-1] += p
                else:
                    out.append(p)
            else:
                out.append(p)
            pos += len(w)
            continue
        if w in PROPER:
            out.append(PROPER[w])
            pos += len(w)
            continue
        piece = ""
        for k in range(len(w)):
            s = syl[pos + k]
            brk = s.startswith(" ")
            s = s.strip()
            m = mark(s)
            if s == "r5" and piece:
                piece += "r"
                continue
            if brk and piece:
                piece += " "
            elif piece and m[:1].lower() in "aeoāáǎàēéěèōóǒò":
                piece += "'"
            piece += m
        if w == "儿" and out:  # erhua written as a separate word: glue it
            out[-1] += "r"
        else:
            out.append(piece)
        pos += len(w)
    text_py = " ".join(x for x in out if x)
    text_py = re.sub(r"\s+–\s*", " – ", text_py)
    text_py = text_py.replace("« ", "« ")
    for i, ch in enumerate(text_py):
        if ch.isalpha():
            text_py = text_py[:i] + ch.upper() + text_py[i + 1:]
            break
    # capitalise after an end-of-sentence mark inside the string
    text_py = re.sub(r"((?:[.!?]|–) (?:– )?)([a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü])", lambda m: m.group(1) + m.group(2).upper(), text_py)
    return text_py


def word_pinyin(word, lex):
    """Mot seul -> pinyin à accents collé (túshūguǎn)."""
    if not word:
        return ""
    if word in lex:
        return join_word([mark(s) for s in lex[word]])
    py = sentence_pinyin(word, lex).replace(" ", "")
    return py[:1].lower() + py[1:] if word not in PROPER else py


def join_word(marked):
    piece = ""
    for m in marked:
        if m == "r" and piece:
            piece += "r"
            continue
        if piece and m[:1].lower() in "aeoāáǎàēéěèōóǒò":
            piece += "'"
        piece += m
    return piece
