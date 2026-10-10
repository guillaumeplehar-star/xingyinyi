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
| `outils/decks.py` | `verifier` (renvois, mots définis deux fois…), `ajouter`, `completer` (pinyin automatique, demande pypinyin), `nouvelle-liste`. |
| `outils/hsk/` | Production des listes HSK 4-6 (2.0) et HSK 1-6 (3.0, programme 2026) : sources sous licence MIT, `inventaire.py`, `lots.py`, `revue.py`, `controle.py`, `assembler.py`, `consignes.md` (rédaction et relecture par agents), `LISEZMOI.md` ; `travail/` est ignoré par git. |
| `outils/pinyin_auto.py`, `lexique_*.tsv`, `syllabes.txt`, `caracteres_hsk1-3.txt` | Pinyin automatique aux conventions des manuels ; liste des caractères HSK 1-3. |
| `outils/version_appli.py` | À lancer après toute modification de l'appli (voir plus bas). |
| `tests/` | Tests Playwright (`test_seance.py`, `test_seaux.py`, `test_listes.py`, `test_dico.py`, aides communes dans `commun.py`) ; `tests/donnees/decks` est une copie figée des listes d'origine, avec les anciens champs `mode`/`parJour` (ne pas la synchroniser avec `decks/` ni la modifier). |
| `LISEZMOI.md` | Guide de l'utilisateur, en français. À tenir à jour quand une fonction visible change. |

## Commandes (PowerShell : une commande par ligne, pas de `&&`)

```powershell
py -m http.server 8000                 # puis http://localhost:8000 (le service worker marche sur localhost)
py tests\test_seance.py                # séance complète, clair et sombre, hors ligne, migration (environ 2 min)
py tests\test_seaux.py                 # seaux, file, réglages des délais, évaluation, migration du planning
py tests\test_listes.py                # listes du téléphone, publication GitHub simulée (environ 1 min)
py tests\test_dico.py                  # dictionnaire : renvois, mot de plusieurs listes, Afficher, partage, publication
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
  `normalizeState`), `xingyinyi.listes` (ancien cache de `decks/`, vidé : le cache est désormais dans Cache Storage,
  cache `listes-xingyinyi`, clé `__listes__.json` ; `readCache`/`writeCache` sont asynchrones ; sw.js ne vide que ses
  propres caches `xingyinyi-…`), `xingyinyi.github` (dépôt et jeton,
  jamais dans les sauvegardes), `xingyinyi.publie` (garde contre les fichiers d'avant une publication : Pages pas encore à jour, copie
  du service worker hors ligne ; voir Publication),
  `xingyinyi.avant-seaux` (`KEY_OLD` : copie brute de l'état d'avant les seaux, écrite une seule fois par
  `loadState` lors de la migration, lue par aucun code ; à garder pour pouvoir récupérer l'ancienne progression).
- **État** : `{v:2, sched:1, settings, cards, edits, custom, lists, tel, listEdits, sent, decks, log, test, learn}`. `custom` :
  mots créés sur le téléphone (définitions, ids `u-…` ; `c` copié pour l'ordinateur, `m` corrigé, en ms) ; `lists` :
  listes du téléphone `{id, nom, ids}` ; `tel` : ids de « Ajoutés ici » ; `listEdits[id] = {add, del}` : mots ajoutés à
  une liste de decks/ non figée ou retirés, en attente de publication ; `sent[id]` : ids qu'une liste du téléphone a
  envoyés à sa jumelle (publication, « Copier pour l'ordinateur »), les seuls que `mergeTel` lui retire une fois
  arrivés. Un mot peut être dans plusieurs listes ou dans aucune. `normalizeState` migre l'ancien champ `l` des
  mots du téléphone (leur liste) vers ces `ids`.
  `settings` : `delays` (délai de chaque seau à partir du seau 1 ; `delays.length` = numéro du
  dernier seau, `topBucket()` ; 1 à 9 délais), `evalSize` (mots par évaluation et par test « nouveau sens »,
  20, de 5 à 100), `learnSize` (mots par apprentissage, 20, de 5 à 50),
  `startFace`, `autoAudio`, `rate`, `toneColors`, `exDetails` (traduction de l'exemple ouverte d'office
  sous la carte), `exOnForm` (phrase sur les faces : caractères sur 形, pinyin sur 音 ; le nom est resté), `exam`.
  `decks[id] = {on, cfgOn, show, cfgShow}` (interrupteurs Réviser et Afficher du téléphone ; `cfgOn`/`cfgShow` = derniers
  `actif`/`afficher` lus dans decks.json, qui l'emportent quand ils changent : `syncDeckSettings` ; `decks.sans.show` :
  mots sans liste dans Mots › Toutes). `log[jour] = {n premières vues,
  r autres révisions, p mots sortis du premier tour}` ; une évaluation ou un test n'y écrit rien.
  `test` : le test complet en cours ou `null` (`cleanTest`, appelé par `normalizeState`) : `{lists choisies,
  n mots au départ, queue mots restants (celui à l'écran compris, retiré seulement une fois noté), ok, ko :
  [id, seau avant la réponse, -1 = mot encore au premier tour]}`, enregistré après chaque réponse.
  `learn` : l'apprentissage en cours ou `null` (`cleanLearn`) : `{ids, got, round, check, queue (mots restants, celui à
  l'écran d'abord), res (réponses du dernier passage)}`, écrit par `learnSave` (début, chaque réponse, `build(keep)`),
  repris au démarrage par `study.resumeLearn` (`useLists` « first »), effacé par `dropLearn` (écran de fin, Arrêter,
  un autre mode lancé).
  Carte (absente = jamais vue) : `{b seau, d jour dû (seau ≥ 1 seulement), k clé de file =
  Date.now() au dernier × (seau 0 seulement ; seau 0 sans k = attend le premier tour), r nb de
  révisions, l oublis (× depuis un seau ≥ 1), t jour de la dernière révision, s jour de la
  première, kn sens connus : bits `1 << face` de départ des cartes réussies, 1 形 caractère, 2 音 pinyin, 4 义
  traduction ; un × le remet à 0}`. `normalizeState` donne `kn = 1 << startFace` (形 si « au hasard ») aux
  cartes de seau ≥ 1 dont `kn` manque ou vaut 0 (passées avant les sens, ou par une ancienne version encore ouverte). L'ancien champ `f` (jour du dernier raté) n'est plus écrit et `normalizeState` l'efface.
  Mot : `h` caractères, `p` pinyin, `f` sens (séparés par `;`), `n` note, `s` texte lu par la voix,
  `e`, `ep`, `ef` (exemple, son pinyin, sa traduction), plus `id`, `home` (liste du fichier qui le définit, `null` pour
  un mot du téléphone, avec `phone: true`), `o` (ligne), `lists` (ses listes, dans l'ordre de `LISTS`).
- **Migrations** (`normalizeState`, aussi appelée par la restauration d'une sauvegarde) : état
  `xingyinyi.v1` (identifiants `h3-…`) ; `sched !== SCHED` (anciennes boîtes de Leitner et quotas
  par jour) : chaque carte repasse au seau 0 sans `d`, `r` et `l` gardés, et
  `migratedSched` (remis à `false` à chaque appel) déclenche un toast prioritaire au démarrage. La migration
  se reconnaît à l'absence de `sched` **et** de `settings.delays` : une ancienne version encore ouverte
  réécrit l'état sans `sched` mais garde `delays`, et ne doit pas relancer la migration. Elle retire aussi `settings.newPerDay` et
  `decks[*].perDay`/`cfgPer`, nettoie `delays` (`cleanDelays`), borne `evalSize` et ramène `b`
  dans [0, `delays.length`]. Une correction `s: ""` (bogue d'une version d'avant : la voix perdait son texte) est
  retirée ; le pinyin en chiffres d'un mot du téléphone (imports d'avant) est écrit avec les accents (`tidyPinyin`).
- **Identifiants** : `<id de liste>:<hanzi>` (`#2`… pour une autre définition des mêmes caractères dans le même
  fichier ; les lignes de renvoi ne comptent pas) ; mots
  créés sur le téléphone : `u-…` ; listes du téléphone : `p-…` ; `tel` = « Ajoutés ici ».
  **Ne jamais changer** le format des identifiants, les `id` de `decks.json` ni les clés de stockage :
  la progression serait perdue. Si un format doit évoluer, ajoute une migration dans `normalizeState`.
- **Listes et dictionnaire** (un mot n'apparaît qu'une fois : mêmes caractères, même pinyin, même sens) :
  `buildLists` (decks.json + `parseTSV`, alias de colonnes `COLMAP`, tolère les espaces à la place des
  tabulations) donne `BASE`, chaque fichier en `items` : `{def}` (ligne avec traduction : définit un mot, `out` si
  colonne `hors_liste`) ou `{ref}` (ligne sans traduction : renvoi par caractères, caractères + pinyin, ou id).
  Entrée de decks.json : `{id, nom, fichier, actif, afficher, fixe, dictionnaire}` (`afficher` vrai par défaut ;
  `fixe` : liste HSK, le téléphone ne la change pas ; `dictionnaire` : fichier de mots sans liste, pas dans `LISTS`) ;
  les anciens champs `mode` et `parJour` sont ignorés. `rebuildDeck` : `DEFS` (définitions d'origine, `original`),
  `DECK` (dictionnaire, corrections appliquées), `LISTS` (listes du téléphone puis `BASE` : ordre du premier tour),
  `L.words` (objets de `DECK`, sans doublon), `L.fileIds` (ids du fichier seul), `w.lists`, `BYID`, `LISTBYID`,
  `FIXED`. `resolveRef` (un mot d'une liste figée d'abord), `refText` (renvoi le plus court qui ne peut désigner aucun
  autre mot du dictionnaire, mots du téléphone compris : caractères seuls, puis avec le pinyin, sinon l'id), `pyKey` (lecture, accents
  ou chiffres), `wordIndex`. `deckOn`/`deckShown` (interrupteurs d'une liste), `onLine(w)` (mot d'une liste active :
  file, évaluation, apprentissage…), `mainList(w)` (sa première liste active : étiquette sous la carte, `listOf`),
  `shownWord`, `editable(L)` (pas figée), `setInList`/`inList`, `sameWords(h, p, not, loose)` (même lecture, sinon
  notée autrement : `sameReading`, 一/不 sans ton propre ; `loose` : un ton neutre vaut aussi tout ton, ce qui peut être
  un autre mot, à confirmer par le sens), `senseFits` (deux traductions ont un sens commun, `senseKey`), `bestSame(h, p, f)`
  (import et formulaire : la même lecture, parmi des homographes celui du même sens ; une lecture qui ne diffère que par
  un ton neutre seulement avec le même sens : 东西 dōngxī « est et ouest » n'est pas 东西 dōngxi), `tidyPinyin` (pinyin en
  chiffres écrit avec les accents : imports, `normalizeState`), `cellsOf`/`headerKeys` (lecture des lignes, partagée par `parseTSV`, `fileRows`, `applyEdit` ; un 汉字 seul
  n'est pas un en-tête).
- **Chargement** : `bootLists` (cache, puis `refreshLists` ; un fichier qui n'arrive pas garde sa copie d'avant) →
  `useLists(src, why)` → `syncDeckSettings`, `rebuildDeck`, `mergeTel` (rien avant le chargement des listes ; un mot du
  téléphone qui a maintenant sa ligne dans decks/ y passe : même lecture d'abord, dans le fichier de sa liste jumelle,
  Perso pour « Ajoutés ici », même nom sinon, liste où il a été ajouté, fichier dictionnaire, puis dans une liste figée ;
  sinon la seule ligne de ces caractères d'un tel fichier au même premier sens, si aucun autre mot n'a sa lecture (pinyin
  corrigé sur l'ordinateur). Corrigé ici après la copie (`m` > `c`), ses champs différents restent en corrections.
  `moveWord` déplace la carte (la plus révisée gagne) et renomme l'id dans les listes, `listEdits`, `sent` et la séance
  (`renameInStudy`) ; quand tous les fichiers sont là (`listsWhole`), les ids disparus quittent les listes du téléphone
  et `listEdits.add` ; puis les listes du téléphone perdent les mots envoyés (`sent`) désormais dans leur jumelle, et
  `listEdits` ce que le fichier contient déjà),
  `dropSameEdits`, `rebuildDeck`, `study.build`.
  `diffLists` rédige le message « Listes mises à jour ».
- **Planning** (seaux et file, demandés par Guillaume) : seaux 0 à `topBucket()`, tout mot commence
  au seau 0, aucun quota par jour. `lineOf(today)` donne la file des listes actives : d'abord les
  mots `inPass` (pas de carte, ou seau 0 sans `k` : le premier tour), liste active par liste active dans l'ordre de
  `LISTS`, chacune dans son ordre, un mot de deux listes une seule fois ; ensuite les mots `missed` (seau 0 avec `k`) et `isDue` (seau ≥ 1, `d` ≤ aujourd'hui), triés
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
  `build(keep)` garde ses listes même désactivées ; `testQueue` : un mot d'une liste qui n'est pas arrivée attend, un mot
  disparu part une fois tous les fichiers là), `"learn"` (apprentissage :
  `startLearn` tire `learnSize` mots du seau 0 des listes actives, `learnPool` ; `study.learn = {ids, got, round,
  check}` ; tours sans `applyGrade` : chaque tour passe les `ids` une fois chacun, dans un ordre au hasard, √ → `got`
  (réussis dans ce tour) ; à la fin du tour, `endRound(last)` : tous dans `got` → `toCheck(last)` lance le dernier
  passage, noté comme la file (√ seau 1) ; sinon nouveau tour, `round + 1`, `got` vidé, nouvel ordre qui ne commence
  pas par la carte qu'on vient de voir, toast « Tour n : … » ; si la dernière carte d'un tour quitte les listes,
  `build(keep)` clôt le tour), `"sens"`
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
  Mots (`renderWords`, `renderDeckTabs`) : onglet `all` « Toutes » (mots des listes affichées, une fois chacun, puis
  mots sans liste ; une recherche parcourt tout le dictionnaire), un onglet par liste, `sans` « Sans liste » ; lignes
  dessinées par paquets (`moreWords`, 150 puis 300, `IntersectionObserver` et bouton `[data-more]`), `wordRowHTML` ;
  `#listbar` pour une liste modifiable (`data-la` = `add`, `share`, `rename`, `delete`). Fiche du mot : ses listes,
  `data-act="lists"` (un interrupteur `data-inl` par liste modifiable). Formulaire : liste (modifiables, « Aucune
  liste », nouvelle) ; un mot déjà au dictionnaire est proposé (`data-take`) et un même mot refusé. Partage :
  `listFileText` (première ligne `# 形音义 : liste « nom »`, renvois pour les mots des listes figées, lignes complètes
  sinon), `shareList` (menu de partage, sinon téléchargement et copie) ; `importSheet` reconnaît ce format
  (`SHARED`) et `importShared` crée une liste du téléphone. Réglages : `deckRowHTML` (interrupteurs
  `.switch[data-deck]` Réviser et `.switch[data-show]` Afficher), `freeRowHTML` (mots sans liste).
  Mots : filtres `data-f` (`new` = `inPass`, `known` = seau ≥ max(1, dernier − 1)), `meterHTML`, `knHTML`
  (形音义 allumés selon `kn`, aussi sous la carte et dans `#kn-counts` de Progrès), `knText` (fiche du mot).
  Progrès : sections Apprentissage (`#learn-go`, `#learn-info`) et Sens connus (`#kn-counts`, `#sens-go`,
  `#sens-info`) ; écran de fin : `#learn-start`.
- **Publication** : `publishGitHub` (API Git Data, un seul commit : trees, commits, refs ; jeton à
  accès fin, permission Contents en lecture et écriture ; nouvelles entrées de decks.json sans
  `mode`) : listes du téléphone dans leur jumelle (lignes complètes pour les mots du téléphone, renvois pour les
  autres), `listEdits` (renvois ajoutés ou retirés ; un mot défini dans le fichier et retiré reçoit `hors_liste`), mots
  du téléphone sans liste dans le fichier dictionnaire (`mots.tsv`, créé au besoin), corrections (`applyEdit` ne compte
  que les lignes de définition) ; `fileRows`/`idsOfFile` lisent le fichier distant ; `pendingCount` compte tout cela (sans les
  mots que la jumelle a déjà ni les ids disparus). « Copier pour l'ordinateur » (`exportRows`) écrit comme la
  publication : un mot du téléphone en entier une fois, un renvoi ailleurs, rien de ce que la jumelle a déjà ; il note
  `sent` et `c`.
  Un mot du téléphone n'est écrit en entier qu'une fois par publication (`placed` : les autres fichiers renvoient à son
  futur id) ; un mot marqué `hors_liste` remis dans sa liste perd son x (`revive`). « Supprimer du dépôt » d'une liste
  qui définit des mots la change en fichier dictionnaire (ses renvois retirés), sinon efface son fichier.
  Puis `stalePages` (garde `xingyinyi.publie` : empreintes des fichiers publiés, `""` pour decks.json, et de ceux
  d'avant, du dépôt et du téléphone) refuse sans limite de temps toute version qui a un fichier d'avant (Pages en
  retard, copie du service worker hors ligne) ; une version changée depuis sur l'ordinateur passe après 15 minutes,
  et toute version lors d'une vérification à la main, en ligne, après 15 minutes.

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
- Phrases d'exemple : contenant le mot, avec les seuls caractères du niveau du mot ou en dessous (HSK 1-3 pour
  `decks/hsk1-3.tsv`, `outils/caracteres_hsk1-3.txt` ; `outils/hsk/controle.py` pour les autres) ; pinyin des manuels
  (tons neutres, 一 et 不 avec leur ton réel, 儿 collé).
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

- Ordre des listes (donc du premier tour) modifiable depuis le téléphone.
