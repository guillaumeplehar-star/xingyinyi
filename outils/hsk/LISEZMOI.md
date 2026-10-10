# Listes HSK 4 à 6 (2.0) et HSK 1 à 6 (3.0) : comment elles sont faites

## Sources (dans `sources/`, à ne pas modifier)

| Fichier | Contenu | Origine |
|---|---|---|
| `hsk2012.tsv` | HSK 2.0, liste officielle de 2012, niveaux 1 à 6 (mot, pinyin, sens anglais) | github.com/glxxyz/hskhsk.com, licence MIT (© 2020 Alan Davies) |
| `hsk2026.tsv` | HSK 3.0, programme d’examen 2026 (新版HSK考试大纲, novembre 2025), niveaux 1 à 6 : mot, homographes numérotés (点1, 点2), pinyin, nature | github.com/Punpuf/hsk-syllabus-vocabulary-parser, licence MIT, extrait du PDF officiel |
| `frequence.tsv` | rang de fréquence des mots, pour l’ordre des listes | github.com/drkameleon/complete-hsk-vocabulary, licence MIT |

Les sens anglais ne servent que d’indices : les sens français, les phrases et leurs traductions
sont rédigés à part.

## Étapes

1. `py outils\hsk\inventaire.py` : fusionne les deux programmes en mots uniques (mêmes caractères,
   même lecture : 一 et 不 comptent quel que soit leur ton, et un ton neutre ne sépare pas deux
   mots d’un programme à l’autre ; deux homographes numérotés restent deux mots). Les mots de
   `decks/hsk1-3.tsv` gardent leur identifiant. Un mot nouveau est défini dans la première liste
   qui le contient, dans l’ordre de publication : HSK 1, 2, 3 (2.0), HSK 1, 2, 3 (3.0), HSK 4 (2.0),
   HSK 4 (3.0), HSK 5 (2.0), HSK 5 (3.0), HSK 6 (2.0), HSK 6 (3.0). Résultat : `inventaire.tsv`.
   Le HSK 2.0 ne numérote pas les homographes : `HOMO_IN` (dans `inventaire.py`) dit lesquels une liste
   2.0 contient (花 du HSK 3 : « dépenser » et « fleur », deux mots ; 等 du HSK 4 : « etc. » seulement),
   `HOMO_OF` rattache un mot existant à l’homographe que montre sa phrase d’exemple (过去 : le passé).
   L’assembleur réduit alors la fiche existante à son sens (`SPLIT`) et ajoute l’autre à la suite.
2. `py outils\hsk\lots.py` : les mots à rédiger, par lots de 60, dans `travail/lots/` (ignoré par
   git) ; les lots déjà rédigés sont gardés. `py outils\hsk\revue.py exporter` prépare la
   relecture des fiches existantes (lots `r01-hsk1` …).
3. Rédaction puis relecture indépendante de chaque lot par Claude Code (consignes :
   `consignes.md`), dans `travail/rediges/` ; journaux des corrections dans `travail/journal/`
   (un lot relu finit son journal `.revue.txt` par `RELU`).
4. `py outils\hsk\controle.py <lot>` : contrôle d’un lot (mot présent dans la phrase, caractères
   du niveau, ponctuation, traduction) et pinyin des phrases (`--garder` garde les corrections).
5. `py outils\hsk\assembler.py` : état des listes ; avec `--ecrire`, écrit dans `decks/` les
   listes dont tous les mots sont relus, dans l’ordre de publication, reporte les corrections des
   fiches existantes et inscrit les listes dans `decks.json` (figées, hors de la file et masquées au
   départ). Puis `py outils\decks.py verifier`, et publier.
