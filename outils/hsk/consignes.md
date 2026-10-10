# Rédaction des fiches HSK : consignes

Pour chaque mot d'un lot (`outils/hsk/travail/lots/NNN-maison.tsv`), une fiche au format des listes de
`decks/` : le sens en français, une note facultative, le texte lu par la voix, une phrase d'exemple et sa
traduction. Les fiches servent à un francophone qui révise le HSK sur son téléphone : elles doivent être
justes avant tout, puis brèves et naturelles. Regarde `decks/hsk3.tsv` pour le ton et la forme attendus.

## Colonnes du lot (entrée)

- `id`, `mot`, `pinyin` : ne pas modifier (le pinyin suit la convention des manuels, voir plus bas ; si tu
  es sûr qu'il est faux, corrige-le et dis pourquoi dans le journal).
- `homographe` : 1 ou 2 quand le programme HSK 2026 distingue deux mots de même écriture et même lecture.
- `nature` : nature du mot dans le programme HSK 2026 (名 nom, 动 verbe, 形 adjectif, 副 adverbe, 量
  classificateur, 介 préposition, 连 conjonction, 助 particule, 代 pronom, 数 nombre, 叹 interjection…) :
  le sens donné doit couvrir ces emplois.
- `niveaux` : `2.0:4` = HSK 2.0 niveau 4, `3.0:3` = HSK 3.0 (2026) niveau 3.
- `anglais` : sens anglais de CC-CEDICT, **indice seulement** (souvent trop large, parfois un autre mot).
- `lie_a` : pour un homographe ou une seconde lecture, le mot voisin (id, pinyin, sens déjà rédigé ou
  attendu) dont ce mot doit se distinguer. Deux homographes ne partagent aucun sens : chacun ne donne que
  le sien (celui de sa `nature`), même si l'indice anglais les mélange ; la note peut renvoyer à l'autre.

## Fichier rédigé (sortie)

`outils/hsk/travail/rediges/NNN-maison.tsv`, UTF-8, colonnes séparées par une tabulation, dans cet ordre,
une ligne d'en-tête puis une ligne par mot du lot (même ordre) :

`id	mot	pinyin	francais	note	audio	exemple	exemple_pinyin	exemple_fr`

Laisse `exemple_pinyin` vide : `py outils\hsk\controle.py NNN-maison` le remplit (voir « Pinyin »).

### francais (obligatoire)

- Le sens le plus courant au niveau du mot d'abord, puis les autres emplois utiles, séparés par « ; »
  (espace avant et après). 1 à 4 sens, brefs : « organiser, arranger ; disposition ».
- Pour un classificateur : « classif. : … » avec un exemple (`一只猫 = un chat`).
- Une construction s'écrit en chinois avec sa traduction : « (跟…一样) », « 把书放在桌子上 = poser le livre
  sur la table ». Pas d'autre chinois dans ce champ.
- Registre si utile : « (soutenu) », « (familier) », « (écrit) ».
- Jamais d'anglais. Pas de calque de l'indice anglais : traduis le mot chinois.

### note (facultative)

Seulement si elle aide vraiment : une autre lecture du même caractère (« aussi hái : encore (HSK 2) »), un
mot proche à ne pas confondre, un emploi piège. Une ligne courte. Pour un homographe : « à distinguer de
点 diǎn (heure ; un peu) ».

### audio

Ce que la voix de l'iPhone doit lire à la place du mot seul quand elle risque de se tromper de lecture :
**toujours** pour un mot d'un seul caractère (un mot courant de 2 à 4 caractères où le caractère a cette
lecture : `还书`, `一只`, `银行`), et pour un mot dont un caractère a plusieurs lectures si la voix peut se
tromper. Sinon, vide.

### exemple (obligatoire)

- Une phrase naturelle, courante, comme dans un bon manuel, qui emploie le mot **dans son premier sens**
  (celui de `francais`). 6 à 20 caractères de préférence, 28 au plus.
- Le mot y figure tel quel (un verbe séparable peut être séparé : 帮了我一个忙).
- **Caractères permis** : ceux des mots HSK du niveau du mot ou en dessous (pour `2.0:4 3.0:3`, les
  caractères des niveaux 1 à 4 du HSK 2.0 et ceux des niveaux 1 à 3 du HSK 3.0), plus ceux du mot.
  `controle.py` signale tout caractère hors niveau : reformule.
- Ponctuation chinoise pleine chasse (，。？！、：“”), pas d'espace, pas de lettres latines, les nombres
  en caractères chinois. Finit par 。, ？, ！ ou ….
- Situations de la vie courante, études, travail, voyages, famille. Pas de politique, de religion, de
  violence, de noms de personnes réelles. Noms propres rares (北京, 中国 vont bien).
- Une phrase qui montre bien le sens (pas « 这是一个 X。 »).

### exemple_fr (obligatoire)

- Traduction **fidèle** de la phrase chinoise, en français naturel (pas mot à mot) : temps et aspect
  (了, 过, 在, 着), négation, quantités, sujet, ton. Rien d'ajouté, rien d'oublié.
- Tutoiement pour 你, vouvoiement pour 您.
- Typographie : apostrophe ’ (jamais '), guillemets « », espace avant ? ! : ; (une espace ordinaire
  suffit), majuscule en début de phrase, point final.

## Pinyin

`controle.py` calcule le pinyin des phrases (`outils/pinyin_auto.py`) selon la convention des manuels :
mots séparés par des espaces, 一 et 不 avec leur ton réel (yí ge, yì qǐ, bú shì ; pas d'autre changement de
ton), particules et mots au ton neutre (de, le, zhe, guo, ma, péngyou, dìfang), 儿 collé (zhèr, yíhuìr),
majuscule en début de phrase et aux noms propres, ponctuation latine (。→ . ，→ , ？→ ?). Il se trompe parfois
sur les caractères à plusieurs lectures (行 xíng / háng, 长, 得, 了 le / liǎo, 地, 着, 还, 重, 为, 都, 只,
觉, 便, 数, 种, 应, 好, 干, 调, 处, 差, 少, 空, 当, 倒, 假, 教, 乐, 背, 难, 中, 相, 要…) : le relecteur
corrige alors la cellule à la main. Après une correction à la main, lance le contrôle avec `--garder`, sinon
il recalcule tout. Si tu changes une phrase, vide sa cellule `exemple_pinyin` pour qu'elle soit recalculée.

## Contrôle

    py outils\hsk\controle.py NNN-maison            (python au lieu de py si py n'existe pas)

Corrige chaque ligne ERREUR, lis chaque « attention » et corrige si besoin, relance jusqu'à 0 erreur.
Ne modifie aucun autre fichier du dépôt.

## Relectures

Deux relectures indépendantes suivent la rédaction, directement dans le fichier rédigé :

1. **Chinois** : la phrase est-elle naturelle et correcte, emploie-t-elle le mot dans le sens donné ? Le
   pinyin de la phrase (polyphones, 一 et 不, tons neutres, 儿) et celui du mot sont-ils justes ? L'audio
   convient-il ?
2. **Français** : le sens est-il juste, complet pour le niveau, bref, sans calque de l'anglais ? La
   traduction de la phrase est-elle fidèle et naturelle (aspect, négation, quantités, rien d'ajouté ni
   d'oublié) ? La note est-elle exacte ? Typographie.

Un relecteur ne corrige que les vraies erreurs ou maladresses (pas de réécriture par goût) et note chaque
changement dans `outils/hsk/travail/journal/NNN-maison.<zh|fr>.txt` : `id<TAB>champ<TAB>avant<TAB>après<TAB>raison`.
