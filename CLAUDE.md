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
- **État** : `{v:2, sched:1, settings, cards, edits, custom, lists, decks, log, test}`.
  `settings` : `delays` (délai de chaque seau à partir du seau 1 ; `delays.length` = numéro du
  dernier seau, `topBucket()` ; 1 à 9 délais), `evalSize` (mots par évaluation et par test « nouveau sens »,
  20, de 5 à 100), `learnSize` (mots par apprentissage, 20, de 5 à 50),
  `startFace`, `autoAudio`, `rate`, `toneColors`, `exDetails` (traduction de l'exemple ouverte d'office
  sous la carte), `exOnForm` (phrase sur les faces : caractères sur 形, pinyin sur 音 ; le nom est resté), `exam`.
  `decks[id] = {on, cfgOn}` (interrupteur du téléphone ; `cfgOn` = dernier `actif` lu dans
  decks.json, qui l'emporte quand il change : `syncDeckSettings`). `log[jour] = {n premières vues,
  r autres révisions, p mots sortis du premier tour}` ; une évaluation ou un test n'y écrit rien.
  `test` : le test complet en cours ou `null` (`cleanTest`, appelé par `normalizeState`) : `{lists choisies,
  n mots au départ, queue mots restants (celui à l'écran compris, retiré seulement une fois noté), ok, ko :
  [id, seau avant la réponse, -1 = mot encore au premier tour]}`, enregistré après chaque réponse.
  Carte (absente = jamais vue) : `{b seau, d jour dû (seau ≥ 1 seulement), k clé de file =
  Date.now() au dernier × (seau 0 seulement ; seau 0 sans k = attend le premier tour), r nb de
  révisions, l oublis (× depuis un seau ≥ 1), t jour de la dernière révision, s jour de la
  première, kn sens connus : bits `1 << face` de départ des cartes réussies, 1 形 caractère, 2 音 pinyin, 4 义
  traduction ; un × le remet à 0}`. `normalizeState` donne `kn = 1 << startFace` (形 si « au hasard ») aux
  cartes de seau ≥ 1 dont `kn` manque ou vaut 0 (passées avant les sens, ou par une ancienne version encore ouverte). L'ancien champ `f` (jour du dernier raté) n'est plus écrit et `normalizeState` l'efface.
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
  `perso:<hanzi>` par exemple, avec tous ses champs, donc sa place dans la file ; `renameInStudy` lui garde sa place
  dans le test enregistré et dans la séance en cours, quel que soit le mode),
  `dropSameEdits`, `rebuildDeck`, `study.build`.
  `diffLists` rédige le message « Listes mises à jour ».
- **Planning** (seaux et file, demandés par Guillaume) : seaux 0 à `topBucket()`, tout mot commence
  au seau 0, aucun quota par jour. `lineOf(today)` donne la file des listes actives : d'abord les
  mots `inPass` (pas de carte, ou seau 0 sans `k` : le premier tour), dans l'ordre de `LISTS` puis
  `o` ; ensuite les mots `missed` (seau 0 avec `k`) et `isDue` (seau ≥ 1, `d` ≤ aujourd'hui), triés
  par `lineKey` (`k` pour un raté, `dayStart(d)` pour un mot dû ; à égalité, `t`). Deux notes
  seulement : `applyGrade(id, ok, kind, face)` (`face` : face de départ, `study.curFace` ; √ allume son bit
  dans `kn`, × met `kn` à 0) ; × → seau 0, `k = Date.now()`, `l++` si le seau était
  ≥ 1, plus de `d` ; √ → seau b+1 (plafonné à `topBucket()`), `d` = aujourd'hui + `delayOf(b)`, plus
  de `k`. `kind` = `"eval"` (évaluation), `"test"` (test complet) ou `"sens"` (nouveau sens) : un √ ne touche ni au
  seau, ni à `d`, ni à `t`, sauf en test pour un mot `inPass`, qui passe au seau 1. Toujours `r++`, `s` à
  la première vue, `logAdd` (sauf en évaluation et en test). Autres aides : `bucketOf`, `delayOf`, `seen` (r > 0), `recomputeDue()`
  après un changement des délais ou du nombre de seaux (`d = t + délai`, seau plafonné), `bucketCounts()`
  (mots déjà passés des listes actives, par seau). La journée
  commence à 4 h (`dayNum`).
- **`study`** : `{queue, cur, mode, res}`. `mode` = `"line"` (la file : `build(keep)` la recalcule
  avec `lineOf`, et `next()` relit la file avant chaque carte : un mot raté se retrouve de lui-même au
  bout), `"free"` (`startFree` : mots vus des
  listes actives mélangés, tous s'il y en a moins de 5 ; aucun effet sur le planning ; un × remet
  le mot au bout), `"eval"` (`startEval` : `evalPick(evalSize)` tire à tour de rôle dans chaque seau
  parmi les mots vus des listes actives, puis mélange ; renvoie `false` avec un toast s'il n'y a
  rien ; `res = {ok, ko}` de paires `[id, seau avant]`), `"test"` (test complet : `testSheet` fait cocher
  les listes, actives au départ, sans toucher à `state.decks` ; `startTest(lists)` mélange tous leurs mots,
  vus ou non, dans `state.test` ; `resumeTest()` le reprend, même après un rechargement ; `res` = `state.test` ;
  `build(keep)` garde ses listes même désactivées et retire les mots disparus), `"learn"` (apprentissage :
  `startLearn` tire `learnSize` mots du seau 0 des listes actives, `learnPool` ; `study.learn = {ids, got, check}` ;
  boucle sans `applyGrade` : √ → `got` et fin de la boucle, × → hors de `got` et 3 cartes plus loin ; quand
  `got` contient tous les `ids`, `toCheck(last)` lance le dernier passage, noté comme la file : √ seau 1 ; si cela
  arrive dans `build(keep)` avec une carte de la boucle à l'écran, elle est abandonnée), `"sens"`
  (nouveau sens : `startSens`, `sensPick(evalSize)` ; la file contient des objets `{id, face}`, lus par `qid` ;
  la carte part de `face`, que `redrawCurrent` garde ; × retire les autres sens du mot et fait passer ses √ du même
  test de `res.ok` à `res.ko` ; `spread` évite deux fois de suite le même mot, dans `sensPick` et après un × ; le
  sélecteur « D'abord » montre la face testée, verrouillé : `renderStartFace`). Note « i sur n » (test, sens, dernier
  passage) : n = réponses données + carte à l'écran + file. `stop()` (« Arrêter », « Pause »
  en test) : une évaluation entamée montre ses résultats partiels, un test se met en pause (écran « Test en
  pause »), sinon retour à la file (`res.cut` : questions restées sans réponse, « Test des sens arrêté »). `next()`
  prend un jeton `tok` : une carte encore en train de glisser (170 ms) n'est pas dessinée si une autre a été demandée entre-temps. `grade(g)` : 0 = ×, 1 = √ (touches
  1 et 2) ; il n'y a plus de 3e note.
- **Interface** : classe `Prism` (rotation 3D, `fit()` ajuste les tailles ; face 音 : pinyin du mot,
  phrase en pinyin `.sound-ex` par `markPinyin` qui souligne les syllabes du mot sans tenir compte des tons,
  boutons `[data-say]` « Mot » et `[data-say-ex]` « Phrase », ou « Écouter » seul sans exemple), bandeau 例
  (`slipHTML`, `renderSlip`, `revealSlip` ; en révision il montre la phrase en caractères et, sous
  « Traduction », sa traduction seulement ; la fiche du mot, mode `full`, y ajoute le pinyin), vues `study`/`words`/`progress`/`settings`,
  bouton ＋ de l'en-tête (`#btn-new`) et recherche sans résultat → `addSheet` (`prefillFrom`),
  feuilles (`openSheet`, `wordSheet` qui indique le seau), `toast(msg, ms, hold)` (applique `frTypo` ; `hold` garde un message important
  à l'écran, le dernier message arrivé entre-temps s'affiche ensuite).
  Révision : `#counts` (`renderCounts` : « à voir » = `inPass`, « à revoir » ; « à évaluer » ou
  « en libre » ou « à tester » hors de la file), étiquettes `renderCardStatus` (« Nouveau mot », « Seau N », « raté »,
  `.chip.test` en évaluation et en test), indications `#gi0`/`#gi1` sous × et √ (`setActions`), `#free-note`
  et `#free-stop` (`renderModeNote`), écran de fin `showDone` (`#done-title`, `#done-text`,
  `#done-more` avec `evalSummary(res)` : score, résultat par seau (« Nouveaux » pour le seau -1 d'un test), mots ratés ; `#done-next` ; boutons
  `#done-back` « Reprendre la file » hors de la file, `#eval-start`, `#free-start`, `#learn-start`, `#done-test` : `renderDoneBtns`,
  aussi appelé par `build(keep)` quand les listes changent sous l'écran de fin).
  Boutons du test (`renderTestBtns`, `testBtnsHTML`, dans `#done-test` et `#test-box` de Progrès, avec
  `#test-info`) : `data-test` = `start`/`resume`/`drop` (confirmation `drop-yes`/`cancel`).
  Progrès (`renderProgress`) : `#seen-n` mots passés, `#projection` (reste du premier tour, rythme
  `passPace` tiré de `log.p`, rythme pour l'examen), `#decktable` (Liste, Passés, À voir), colonnes
  des seaux `#boxes`/`#boxes-axis` par `drawCols` (`--n` posé en JS ; seau 0 = mots ratés), boutons
  `#eval-go`/`#free-go`, `#eval-info`, `#forecast` (7 jours). Réglages (`renderSettings`) :
  `#new-order`, `#deck-settings` (`.switch[data-deck]`), seaux `#bucket-settings`
  (`bucketRowsHTML`, `button[data-delay][data-b]`, `stepDelay` sur `DELAY_STEPS`) et
  `#bucket-btns` (`bucketBtnsHTML`, `data-bk` = `add`/`remove`/`reset`), `#eval-minus`/`#eval-plus`.
  Mots : filtres `data-f` (`new` = `inPass`, `known` = seau ≥ max(1, dernier − 1)), `meterHTML`, `knHTML`
  (形音义 allumés selon `kn`, aussi sous la carte et dans `#kn-counts` de Progrès), `knText` (fiche du mot).
  Progrès : sections Apprentissage (`#learn-go`, `#learn-info`) et Sens connus (`#kn-counts`, `#sens-go`,
  `#sens-info`) ; écran de fin : `#learn-start`.
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
