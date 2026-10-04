# 形音义 : guide pour Claude Code

Appli de flashcards pour le chinois : chaque carte est un prisme à trois faces, 形 caractère,
音 pinyin, 义 sens en français, plus une phrase d'exemple 例 sous la carte. Utilisateur : Guillaume,
francophone, qui prépare le HSK 3 (format HSK 2.0, examen le 29 novembre 2026). Usage principal sur
iPhone, appli installée depuis Safari sur l'écran d'accueil, hors ligne. Ordinateur sous Windows
(PowerShell). Réponds en français.

**Ce dépôt est le site publié** (GitHub Pages, branche `main`, racine). Pas de framework, pas de
compilation : `index.html` contient tout le HTML, le CSS et le JavaScript. C'est le fichier à modifier.

## Fichiers

| Chemin | Rôle |
|---|---|
| `index.html` | L'appli entière (environ 2 500 lignes). |
| `sw.js` | Service worker : réseau d'abord (4 s au plus), sinon copie locale ; garde l'appli hors ligne. |
| `manifest.webmanifest`, `*.png` | Installation sur l'écran d'accueil. |
| `fonts/` | Sous-ensembles de LXGW WenKai (police `"WK"`, environ 3 040 caractères : HSK 2.0 niveaux 1-6 et HSK 3.0) et d'Andika (police `"AndikaX"`, latin). Licence OFL. |
| `decks/` | Les listes de mots : `decks.json` et un `.tsv` par liste. Source de vérité, modifiée par Guillaume, par toi, et par le téléphone (publication via l'API GitHub). |
| `outils/decks.py` | `verifier`, `ajouter`, `completer` (pinyin automatique, demande pypinyin), `nouvelle-liste`. |
| `outils/pinyin_auto.py`, `lexique_*.tsv`, `syllabes.txt`, `caracteres_hsk1-3.txt` | Pinyin automatique aux conventions des manuels ; liste des caractères HSK 1-3. |
| `outils/version_appli.py` | À lancer après toute modification de l'appli (voir plus bas). |
| `tests/` | Tests Playwright (`test_seance.py`, `test_seaux.py`, `test_listes.py`, aides communes dans `commun.py`) ; `tests/donnees/decks` est une copie figée des listes d'origine, avec les anciens champs `mode`/`parJour` (ne pas la synchroniser avec `decks/` ni la modifier). |
| `LISEZMOI.md` | Guide de l'utilisateur, en français. À tenir à jour quand une fonction visible change. |

## Commandes (PowerShell : une commande par ligne, pas de `&&`)

```powershell
py -m http.server 8000                 # puis http://localhost:8000 (le service worker marche sur localhost)
py tests\test_seance.py                # séance complète, clair et sombre, hors ligne, migration (environ 2 min)
py tests\test_seaux.py                 # seaux, file, réglages des délais, évaluation, migration du planning
py tests\test_listes.py                # listes du téléphone, publication GitHub simulée (environ 1 min)
py outils\decks.py verifier            # contrôle de decks/
py outils\version_appli.py             # après une modification de index.html, sw.js, des icônes ou des polices
```

Prérequis des tests (une fois) : `py -m pip install playwright pypinyin` puis
`py -m playwright install chromium`. Les tests s'arrêtent avec le code 1 en cas d'échec ou d'erreur
dans la console ; captures d'écran dans `tests/sortie/captures` (ignoré par git).

`version_appli.py` met à jour `const BUILD` (date affichée dans Réglages) et `VERSION` dans `sw.js`.
Sans lui, les téléphones gardent l'ancienne version en cache sans afficher « Nouvelle version prête ».
Une simple modification de `decks/` n'en a pas besoin : l'appli relit les listes à l'ouverture.

Publier : `git add -A`, `git commit -m "…"`, `git push` ; GitHub Pages met une à deux minutes. Sur
l'iPhone : Réglages › Appli › Vérifier. Le téléphone peut lui aussi écrire dans le dépôt : fais
`git pull` avant de modifier `decks/`.

## Repères dans index.html

- **Constantes du haut** : `EMBEDDED` (null ici ; servait à l'aperçu claude.ai), `COVER` (caractères
  présents dans la police), `SYLL` (421 syllabes, ü noté v), `LEGACY` (ordre officiel HSK 3 pour
  migrer la première version), `IS_PWA`, `XH` (hauteur d'x d'Andika), `BUILD`. Planning :
  `DELAYS = [1,3,7,14,30,60]` (délais par défaut des seaux 1 à 6, en jours), `DELAY_STEPS` (crans
  des boutons − / + des délais, de 1 à 365 jours), `MAX_BUCKETS = 10` (seaux 0 à 9 au plus),
  `SCHED = 1` (format du planning, enregistré dans l'état sous `sched`).
- **Pinyin** : `parsePinyin` accepte les accents (découpage en syllabes par programmation dynamique
  sur `SYLL` ; une syllabe interne ne commence jamais par a/o/e sans apostrophe ; le r du 儿 est
  collé) ou les chiffres (`tu2shu1guan3`). `pinyinHTML` produit des `<span class="t1…t5">` ;
  `fold()` sert à la recherche sans accents.
- **Stockage local** : `xingyinyi.v2` (état), `xingyinyi.v1` (première version, migrée par
  `normalizeState`), `xingyinyi.listes` (cache de `decks/`), `xingyinyi.github` (dépôt et jeton,
  jamais dans les sauvegardes), `xingyinyi.publie` (garde contre GitHub Pages pas encore à jour),
  `xingyinyi.avant-seaux` (`KEY_OLD` : copie brute de l'état d'avant les seaux, écrite une seule fois par
  `loadState` lors de la migration, lue par aucun code ; à garder pour pouvoir récupérer l'ancienne progression).
- **État** : `{v:2, sched:1, settings, cards, edits, custom, lists, decks, log}`.
  `settings` : `delays` (délai de chaque seau à partir du seau 1 ; `delays.length` = numéro du
  dernier seau, `topBucket()` ; 1 à 9 délais), `evalSize` (mots par évaluation, 20, de 5 à 100),
  `startFace`, `autoAudio`, `rate`, `toneColors`, `exDetails`, `exOnForm`, `exam`.
  `decks[id] = {on, cfgOn}` (interrupteur du téléphone ; `cfgOn` = dernier `actif` lu dans
  decks.json, qui l'emporte quand il change : `syncDeckSettings`). `log[jour] = {n premières vues,
  r autres révisions, p mots sortis du premier tour}` ; une évaluation n'y écrit rien.
  Carte (absente = jamais vue) : `{b seau, d jour dû (seau ≥ 1 seulement), k clé de file =
  Date.now() au dernier × (seau 0 seulement ; seau 0 sans k = attend le premier tour), r nb de
  révisions, l oublis (× depuis un seau ≥ 1), t jour de la dernière révision, s jour de la
  première}`. L'ancien champ `f` (jour du dernier raté) n'est plus écrit et `normalizeState` l'efface.
  Mot : `h` caractères, `p` pinyin, `f` sens (séparés par `;`), `n` note, `s` texte lu par la voix,
  `e`, `ep`, `ef` (exemple, son pinyin, sa traduction), plus `id`, `deck`, `o` (ordre).
- **Migrations** (`normalizeState`, aussi appelée par la restauration d'une sauvegarde) : état
  `xingyinyi.v1` (identifiants `h3-…`) ; `sched !== SCHED` (anciennes boîtes de Leitner et quotas
  par jour) : chaque carte repasse au seau 0 sans `d`, `r` et `l` gardés, et
  `migratedSched` (remis à `false` à chaque appel) déclenche un toast prioritaire au démarrage. La migration
  se reconnaît à l'absence de `sched` **et** de `settings.delays` : une ancienne version encore ouverte
  réécrit l'état sans `sched` mais garde `delays`, et ne doit pas relancer la migration. Elle retire aussi `settings.newPerDay` et
  `decks[*].perDay`/`cfgPer`, nettoie `delays` (`cleanDelays`), borne `evalSize` et ramène `b`
  dans [0, `delays.length`].
- **Identifiants** : `<id de liste>:<hanzi>` (`#2`… pour un doublon dans la même liste) ; mots
  créés sur le téléphone : `u-…` ; listes du téléphone : `p-…` ; `tel` = « Ajoutés ici ».
  **Ne jamais changer** le format des identifiants, les `id` de `decks.json` ni les clés de stockage :
  la progression serait perdue. Si un format doit évoluer, ajoute une migration dans `normalizeState`.
- **Listes** : `buildLists` (decks.json + `parseTSV`, alias de colonnes `COLMAP`, tolère les
  espaces à la place des tabulations) donne `BASE`. Entrée de decks.json : `{id, nom, fichier,
  actif}` ; les anciens champs `mode` et `parJour` sont ignorés (`verifier` les signale).
  `LISTS` = listes du téléphone puis `BASE` ; c'est l'ordre du premier tour. `DECK` = tous les
  mots, corrections appliquées ; index `BYID`, `LISTBYID`. `deckOn(id)` dit si une liste est active.
- **Chargement** : `bootLists` (cache, puis `refreshLists`) → `useLists(src, why)` →
  `syncDeckSettings`, `mergeTel` (un mot du téléphone passe dans sa liste jumelle du dépôt : Perso
  pour « Ajoutés ici », même nom sinon ; sa carte `u-…` passe à l'identifiant du mot jumeau,
  `perso:<hanzi>` par exemple, avec tous ses champs, donc sa place dans la file),
  `dropSameEdits`, `rebuildDeck`, `study.build`.
  `diffLists` rédige le message « Listes mises à jour ».
- **Planning** (seaux et file, demandés par Guillaume) : seaux 0 à `topBucket()`, tout mot commence
  au seau 0, aucun quota par jour. `lineOf(today)` donne la file des listes actives : d'abord les
  mots `inPass` (pas de carte, ou seau 0 sans `k` : le premier tour), dans l'ordre de `LISTS` puis
  `o` ; ensuite les mots `missed` (seau 0 avec `k`) et `isDue` (seau ≥ 1, `d` ≤ aujourd'hui), triés
  par `lineKey` (`k` pour un raté, `dayStart(d)` pour un mot dû ; à égalité, `t`). Deux notes
  seulement : `applyGrade(id, ok, test)` ; × → seau 0, `k = Date.now()`, `l++` si le seau était
  ≥ 1, plus de `d` ; √ → seau b+1 (plafonné à `topBucket()`), `d` = aujourd'hui + `delayOf(b)`, plus
  de `k`. `test` (évaluation) : un √ ne touche ni au seau, ni à `d`, ni à `t`. Toujours `r++`, `s` à
  la première vue, `logAdd` (sauf en évaluation). Autres aides : `bucketOf`, `delayOf`, `seen` (r > 0), `recomputeDue()`
  après un changement des délais ou du nombre de seaux (`d = t + délai`, seau plafonné), `bucketCounts()`
  (mots déjà passés des listes actives, par seau). La journée
  commence à 4 h (`dayNum`).
- **`study`** : `{queue, cur, mode, res}`. `mode` = `"line"` (la file : `build(keep)` la recalcule
  avec `lineOf`, et `next()` relit la file avant chaque carte : un mot raté se retrouve de lui-même au
  bout), `"free"` (`startFree` : mots vus des
  listes actives mélangés, tous s'il y en a moins de 5 ; aucun effet sur le planning ; un × remet
  le mot au bout), `"eval"` (`startEval` : `evalPick(evalSize)` tire à tour de rôle dans chaque seau
  parmi les mots vus des listes actives, puis mélange ; renvoie `false` avec un toast s'il n'y a
  rien ; `res = {ok, ko}` de paires `[id, seau avant]`). `stop()` (« Arrêter ») : une évaluation
  entamée montre ses résultats partiels, sinon retour à la file. `grade(g)` : 0 = ×, 1 = √ (touches
  1 et 2) ; il n'y a plus de 3e note.
- **Interface** : classe `Prism` (rotation 3D, `fit()` ajuste les tailles), bandeau 例
  (`slipHTML`, `renderSlip`, `revealSlip`), vues `study`/`words`/`progress`/`settings`,
  bouton ＋ de l'en-tête (`#btn-new`) et recherche sans résultat → `addSheet` (`prefillFrom`),
  feuilles (`openSheet`, `wordSheet` qui indique le seau), `toast(msg, ms, hold)` (applique `frTypo` ; `hold` garde un message important
  à l'écran, le dernier message arrivé entre-temps s'affiche ensuite).
  Révision : `#counts` (`renderCounts` : « à voir » = `inPass`, « à revoir » ; « à évaluer » ou
  « en libre » hors de la file), étiquettes `renderCardStatus` (« Nouveau mot », « Seau N », « raté »,
  `.chip.test` en évaluation), indications `#gi0`/`#gi1` sous × et √ (`setActions`), `#free-note`
  et `#free-stop` (`renderModeNote`), écran de fin `showDone` (`#done-title`, `#done-text`,
  `#done-more` avec `evalSummary` : score, résultat par seau, mots ratés ; `#done-next` ; boutons
  `#done-back` « Reprendre la file » hors de la file, `#eval-start`, `#free-start`).
  Progrès (`renderProgress`) : `#seen-n` mots passés, `#projection` (reste du premier tour, rythme
  `passPace` tiré de `log.p`, rythme pour l'examen), `#decktable` (Liste, Passés, À voir), colonnes
  des seaux `#boxes`/`#boxes-axis` par `drawCols` (`--n` posé en JS ; seau 0 = mots ratés), boutons
  `#eval-go`/`#free-go`, `#eval-info`, `#forecast` (7 jours). Réglages (`renderSettings`) :
  `#new-order`, `#deck-settings` (`.switch[data-deck]`), seaux `#bucket-settings`
  (`bucketRowsHTML`, `button[data-delay][data-b]`, `stepDelay` sur `DELAY_STEPS`) et
  `#bucket-btns` (`bucketBtnsHTML`, `data-bk` = `add`/`remove`/`reset`), `#eval-minus`/`#eval-plus`.
  Mots : filtres `data-f` (`new` = `inPass`, `known` = seau ≥ max(1, dernier − 1)), `meterHTML`.
- **Publication** : `publishGitHub` (API Git Data, un seul commit : trees, commits, refs ; jeton à
  accès fin, permission Contents en lecture et écriture ; nouvelles entrées de decks.json sans
  `mode`), puis `stalePages` ignore les anciens fichiers servis par Pages pendant au plus 15 minutes.

## Conventions

- Textes de l'interface en français, tutoiement, majuscule en début de phrase seulement.
  Typographie : espace fine insécable (constante `NB`) avant `: ; ! ?`, apostrophe `’`,
  guillemets « », nombre et nom liés par une espace insécable (`plural`).
- Couleurs des tons fixes (`--t1` rouge, `--t2` orange, `--t3` bleu, `--t4` violet, `--t5` gris),
  thèmes clair (cahier d'écolier) et sombre (tableau noir) par jetons CSS sur `:root`,
  `prefers-color-scheme` et `[data-theme]`. Toute nouvelle couleur passe par un jeton défini dans les
  trois blocs.
- Polices : `--zh` (WenKai) pour le chinois, `--ui` (Andika : a et g à une boucle, comme à l'école).
  Un mot dont un caractère manque à la police prend la classe `.sysfont` (`covered()`).
- Phrases d'exemple : seulement des caractères HSK 1-3 (`outils/caracteres_hsk1-3.txt`), contenant le
  mot ; pinyin des manuels (tons neutres, 一 et 不 avec leur ton réel, 儿 collé).
- iPhone : pas de `alert`/`confirm`/`prompt` (confirmations dans la page), champs en 16 px au moins
  (sinon Safari zoome), zones de sécurité `env(safe-area-inset-*)`, cibles tactiles d'au moins 34 px,
  `prefers-reduced-motion` respecté.
- JavaScript sans dépendance ni bibliothèque externe, dans `index.html`. Pas de `console.log` laissé.
- Messages et sorties des outils Python en UTF-8 (ils forcent `reconfigure`) ; commandes affichées en
  syntaxe Windows (`py outils\…`).

## Vérifier un changement

1. `py tests\test_seance.py`, `py tests\test_seaux.py` et `py tests\test_listes.py` ; ajoute un test
   pour toute nouvelle fonction. Tout changement du planning (seaux, file, évaluation, migration)
   passe par `tests/test_seaux.py`.
2. Regarde le résultat : captures dans `tests/sortie/captures`, ou `py -m http.server 8000` avec les
   outils de développement du navigateur en mode iPhone (390 × 844), en clair et en sombre.
3. Si le format des cartes ou du planning change encore : incrémente `SCHED` et écris la migration
   dans `normalizeState` (les sauvegardes restaurées y passent aussi).
4. `py outils\version_appli.py`, mise à jour de `LISEZMOI.md` si l'usage change, puis commit et push.

## Idées en attente

- Listes HSK 3.0 (niveaux 1 à 3) avec traductions françaises et phrases d'exemple, au même format.
- Ordre des listes (donc du premier tour) modifiable depuis le téléphone.
