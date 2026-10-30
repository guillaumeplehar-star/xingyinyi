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
| `traits/`, `outils/traits.py` | Ordre des traits : `00.json`…`31.json` (caractère rangé par code % 32 → contours SVG des traits et lignes médianes, repère 1024 × 1024, y vers le haut, base à 900), `index.json` (version `v`), `ARPHICPL.TXT` (licence Arphic Public License, à garder telle quelle). Produits par `py outils\traits.py <graphics.txt>` depuis Make Me a Hanzi (github.com/skishore/makemeahanzi, fichier non gardé dans le dépôt) pour les caractères de `COVER`. |
| `outils/cles.py` | Clés (部首) des caractères pour la recherche par clé : lit la base Unihan d'Unicode (`Unihan.zip` et `CJKRadicals.txt` de unicode.org, non gardés dans le dépôt ; licence Unicode) et réécrit la ligne `const CLES = …;` de `index.html` pour les caractères de `COVER` et de `decks/` ; le nombre de traits d'un caractère vient de `traits/` (Unihan compte 艹, 辶… comme les formes anciennes : 草 10 au lieu de 9), sinon traits de la clé + traits restants. Formes de côté (`FORMS` : 亻 pour 人…) et traits des formes simplifiées (`STROKES` : 艹 3, 辶 3, 阝 2…) fixés dans l'outil. |
| `outils/sync/` | Serveur de synchronisation des appareils : `worker.mjs` (Cloudflare Worker + base D1 liée sous le nom `DB`, un document versionné par code, 409 sur une version dépassée, une copie par jour, 30 au plus), `serveur_local.mjs` (le même avec `node:sqlite`, pour les tests et pour essayer), `LISEZMOI.md` (adresses ; mise en place : `LISEZMOI.md` principal, section 7.4). |
| `tests/` | Tests Playwright (`test_seance.py`, `test_seaux.py`, `test_listes.py`, `test_dico.py`, `test_affichage.py` (onglet Affichage), `test_dessin.py` (recherche en dessinant et par clé), `test_sync.py` deux appareils et le serveur local, avec le test et l'apprentissage partagés, aides communes dans `commun.py`) et `test_serveur_sync.mjs` (le serveur seul, Node) ; `tests/donnees/decks` est une copie figée des listes d'origine, avec les anciens champs `mode`/`parJour` (ne pas la synchroniser avec `decks/` ni la modifier). |
| `LISEZMOI.md` | Guide de l'utilisateur, en français. À tenir à jour quand une fonction visible change. |

## Commandes (PowerShell : une commande par ligne, pas de `&&`)

```powershell
py -m http.server 8000                 # puis http://localhost:8000 (le service worker marche sur localhost)
py tests\test_seance.py                # séance complète, clair et sombre, hors ligne, migration (environ 2 min)
py tests\test_seaux.py                 # seaux, file, réglages des délais, évaluation, migration du planning
py tests\test_listes.py                # listes du téléphone, publication GitHub simulée (environ 1 min)
py tests\test_dico.py                  # dictionnaire : renvois, mot de plusieurs listes, Afficher, partage, publication
py tests\test_affichage.py             # Affichage : thèmes, taille du texte, police, grille, pinyin en chiffres, tons, animations
py tests\test_dessin.py                # Mots : caractère dessiné (reconnaissance sans ordre des traits), au doigt et à la souris
py tests\test_sync.py                  # deux appareils synchronisés par le serveur local (demande Node 22.13 ou plus)
node tests\test_serveur_sync.mjs       # le serveur de synchronisation seul
node outils\sync\serveur_local.mjs     # le serveur de synchronisation sur http://localhost:8787
py outils\decks.py verifier            # contrôle de decks/
py outils\version_appli.py             # après une modification de index.html, sw.js, des icônes ou des polices
py outils\traits.py <graphics.txt>     # refaire traits/ (ordre des traits), ARPHICPL.TXT à côté de graphics.txt
py outils\cles.py <dossier Unihan> <CJKRadicals.txt>   # refaire CLES (clés des caractères) dans index.html
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

- **Affichage, avant le premier rendu** (`<script>` à la fin de `<head>`) : `LOOK` (valeurs permises : `themes`, `dark`,
  `text` (facteurs de taille), `zh`, `grid`, `tones`, `motion`), `applyLook(settings)` pose sur `<html>` `data-theme` (absent :
  Automatique), `data-mode` (`dark`/`light` effectif, pour les couleurs des tons), `--tz` et `data-text` (taille du texte),
  `data-zh`, `data-grid`, `data-tones`, `data-motion="reduce"` (choix d'Affichage ou de l'appareil : `reducedMotion()`),
  `data-compact`, et la couleur des `<meta name="theme-color">` ; lancé d'abord sur les réglages lus dans `xingyinyi.v2`, puis
  par `init`, `setLook`, `applyDoc`, `reloadState`, la restauration, et quand le mode clair ou sombre de l'appareil change.
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
  cache `traits-xingyinyi` (paquets de `traits/`, gardés hors ligne ; sw.js laisse passer `traits/` sans y toucher) et
  `xingyinyi.traits` (version des paquets gardés), `xingyinyi.sync` (synchronisation : `{url, code, key = SHA-256 de
  "xingyinyi:" + code, at dernière réussite, err dernier échec, listsAt}`, jamais dans les sauvegardes) et `xingyinyi.sync-base`
  (`{v, doc}` : le dernier document échangé avec le serveur, base de la fusion), `xingyinyi.sync-pending` (empreintes
  `docHash` des derniers envois : un envoi reçu par le serveur dont la réponse s'est perdue devient la base, `ours`), `xingyinyi.avant-seaux` (`KEY_OLD` : copie brute de l'état d'avant les seaux, écrite une seule fois par
  `loadState` lors de la migration, lue par aucun code ; à garder pour pouvoir récupérer l'ancienne progression).
- **État** : `{v:2, sched:1, settings, cards, edits, custom, lists, tel, listEdits, sent, decks, log, moved, test, learn, learnLog, ended}`. `custom` :
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
  sous la carte), `exOnForm` (phrase sur les faces : caractères sur 形, pinyin sur 音 ; le nom est resté), `exam` ; Affichage :
  `theme` (`auto`, `light` Cahier, `paper`, `sepia`, `contrast`, `dark` Tableau noir, `night`), `textSize` (`s`, `m`, `l`,
  `xl`), `zhFont` (`kai`, `hei`, `song`), `grid` (`tian`, `mi`, `none`), `pinyinNum`, `tonePalette` (`app`, `pleco`, `mdbg` ;
  « Aucune » = `toneColors` faux), `motion` (`auto`, `full`, `reduce`), `compact` ; `normalizeState` remet une valeur inconnue
  à celle de `DEFAULTS`.
  `decks[id] = {on, cfgOn, show, cfgShow}` (interrupteurs Réviser et Afficher du téléphone ; `cfgOn`/`cfgShow` = derniers
  `actif`/`afficher` lus dans decks.json, qui l'emportent quand ils changent : `syncDeckSettings` ; `decks.sans.show` :
  mots sans liste dans Mots › Toutes). `log[jour] = {n premières vues,
  r autres révisions, p mots sortis du premier tour}` ; une évaluation ou un test n'y écrit rien.
  `test` : le test complet en cours ou `null` (`cleanTest`, appelé par `normalizeState`) : `{lists choisies,
  n mots au départ, queue mots restants (celui à l'écran compris, retiré seulement une fois noté), ok, ko :
  [id, seau avant la réponse, -1 = mot encore au premier tour], start (`newStart` : l'heure du début, jamais celle de
  l'apprentissage ni d'un fini ; le même test sur chaque appareil ; un test ou un apprentissage d'une version d'avant en
  reçoit un au chargement, `loadState`), at (dernière
  réponse)}`, enregistré après chaque réponse ; fini (dès la dernière réponse, dans `grade` : `study.res` le garde pour
  l'écran de fin) ou abandonné : `endTest`.
  `learn` : l'apprentissage en cours ou en pause, ou `null` (`cleanLearn`) : `{ids, got, round, check, queue (mots
  restants, celui à l'écran d'abord), res (réponses du dernier passage), start (comme le test), at (dernier changement),
  pause}`, écrit par `learnSave` (début, chaque réponse, `build(keep)` ; `at` ne change qu'avec le contenu, sinon la
  synchronisation repartirait sans fin) ; `pause` (propre à l'appareil, hors du document partagé) : en attente ici, pas
  repris au démarrage ; sinon repris au démarrage par `study.resumeLearn("start")` (`useLists` « first ») ; fini (une
  ligne dans `learnLog`, dès la dernière réponse du dernier passage : `closeLearn` dans `grade`), abandonné ou vidé :
  `endLearn`. Un seul à la fois. `learnLog` : les apprentissages finis, le
  plus récent d'abord, `{start, at (fin), rounds, ok, ko (ids réussis et ratés au dernier passage)}` (`cleanLearnLog`,
  `LEARN_LOG_MAX` = 100 ; Progrès suit `state.moved` pour un id changé). `ended` : `start` des apprentissages et des tests
  finis ou abandonnés (`noteEnded`, `ENDED_MAX` = 40), pour que la fusion des appareils ne les fasse pas revenir.
  Carte (absente = jamais vue) : `{b seau, d jour dû (seau ≥ 1 seulement), k clé de file =
  Date.now() au dernier × (seau 0 seulement ; seau 0 sans k = attend le premier tour), r nb de
  révisions, l oublis (× depuis un seau ≥ 1), t jour de la dernière révision, s jour de la
  première, kn sens connus : bits `1 << face` de départ des cartes réussies, 1 形 caractère, 2 音 pinyin, 4 义
  traduction ; un × le remet à 0}`. `normalizeState` donne `kn = 1 << startFace` (形 si « au hasard ») aux
  cartes de seau ≥ 1 dont `kn` manque ou vaut 0 (passées avant les sens, ou par une ancienne version encore ouverte). L'ancien champ `f` (jour du dernier raté) n'est plus écrit et `normalizeState` l'efface.
  Mot : `h` caractères, `p` pinyin, `f` sens (séparés par `;` ou `；` hors parenthèses : `senses`, pour la carte, Mots, la
  fiche, la recherche par clé, `senseKey`, `mergeTel`), `n` note, `s` texte lu par la voix,
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
  notée autrement : `sameReading`, 一/不 sans ton propre, `TONELESS` ; `loose` : un ton neutre vaut aussi tout ton, ce qui peut être
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
  `moveWord` déplace la carte (la plus avancée gagne, `cardAhead` ; noté dans `state.moved`, ancien id → nouvel id) et renomme l'id dans les listes, `listEdits`, `sent` et la séance
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
  `build(keep)` garde ses listes même désactivées et n'enregistre que si `testQueue` change la file ; `testQueue` : un mot
  d'une liste qui n'est pas arrivée attend, un mot disparu part une fois les listes d'ici complètes et à jour,
  `listsSettled`), `"learn"` (apprentissage :
  `startLearn` tire `learnSize` mots du seau 0 des listes actives, `learnPool` ; `study.learn = {ids, got, round,
  check}` ; tours sans `applyGrade` : chaque tour passe les `ids` une fois chacun, dans un ordre au hasard, √ → `got`
  (réussis dans ce tour) ; à la fin du tour, `endRound(last)` : tous dans `got` → `toCheck(last)` lance le dernier
  passage, noté comme la file (√ seau 1) ; sinon nouveau tour, `round + 1`, `got` vidé, nouvel ordre qui ne commence
  pas par la carte qu'on vient de voir, toast « Tour n : … » ; si la dernière carte d'un tour quitte les listes,
  `build(keep)` clôt le tour ; un mot sorti du seau 0 ailleurs entre-temps, sauf s'il a répondu au dernier passage, quitte
  l'apprentissage, `learnKeeps` ; « Pause » (`stop()`) : `pauseLearn` l'enregistre avec `pause`, `study.learn = null`
  (`learnLive()` faux) et l'écran de fin dit « Apprentissage en pause » (`learnText`) ; un autre mode lancé
  (`startFree`, `startEval`, `startSens`, `resumeTest`) le met aussi en pause, avec un toast ; `resumeLearn(why)` :
  `"start"`, `"resume"` (« Reprendre l'apprentissage » ; `startLearn` avec un apprentissage enregistré le reprend),
  `"follow"` (un autre appareil ou une autre fenêtre l'a fait avancer : la carte à l'écran reste si elle vient en premier ;
  pendant le délai d'une réponse, `busy`, seule la file change), `"back"` (de même, mais l'autre version est moins avancée :
  copie du serveur) ; tous ses mots partis : `endLearn`, toast ; un mot d'une liste pas encore là (`listsSettled()` faux :
  un fichier manque, ou un autre appareil a des listes plus récentes) : rien n'est retiré, `waitLearn(LEARN_WAIT)` met
  la séance sur l'écran de pause (« Reprendre » relit les listes, `refreshLists`, au plus toutes les 15 s) (aussi dans `build(keep)`), comme un autre apprentissage arrivé à sa place ; fini :
  `closeLearn` (`L.over`, `L.learnt`, ligne de `learnLog`) à la dernière réponse du dernier passage, sinon dans `showDone`
  (vidé) ; « Pause » sur un apprentissage déjà fini montre sa fin), `"sens"`
  (nouveau sens : `startSens`, `sensPick(evalSize)` : les mots des seaux les plus élevés d'abord, au hasard dans un même seau ; la file contient des objets `{id, face}`, lus par `qid` ;
  la carte part de `face`, que `redrawCurrent` garde ; × retire les autres sens du mot et fait passer ses √ du même
  test de `res.ok` à `res.ko` ; `spread` évite deux fois de suite le même mot, dans `sensPick` et après un × ; le
  sélecteur « D'abord » montre la face testée, verrouillé : `renderStartFace`). Note « i sur n » (test, sens, dernier
  passage) : n = réponses données + carte à l'écran + file. `stop()` (« Arrêter », « Pause »
  en test et en apprentissage) : une évaluation entamée montre ses résultats partiels, un test ou un apprentissage se
  met en pause (écran « Test en pause », « Apprentissage en pause »), sinon retour à la file (`res.cut` : questions restées sans réponse, « Test des sens arrêté »). `next()`
  prend un jeton `tok` : une carte encore en train de glisser (170 ms) n'est pas dessinée si une autre a été demandée entre-temps. `grade(g)` : 0 = ×, 1 = √ (touches
  1 et 2) ; il n'y a plus de 3e note.
- **Interface** : classe `Prism` (rotation 3D ; un clic de souris à gauche du milieu de `root` tourne en arrière, 形 义 音, à droite
  et au toucher en avant, 形 音 义 ; glisser et les flèches choisissent le sens ; `fit()` ajuste les tailles, `layout()` rétrécit la carte quand la hauteur manque avec un texte agrandi ; face 形 : cases 田字格 `.tzg`, phrase
  `.form-ex`, bouton `[data-trace-form]` « Traits » (`traceForm` : chaque caractère tracé dans sa case par un `traceSVG`
  posé sur la police, `.tz-tr`, la police cachée par `.tzg.tracing`) et `[data-steps]` « Décomposer » (`showSteps` :
  feuille avec `renderTraits` en révision, défilement jusqu'à `#sheet-traits` dans la fiche du mot) ; face 音 : pinyin du mot,
  phrase en pinyin `.sound-ex` par `markPinyin` qui souligne les syllabes du mot sans tenir compte des tons (syllabe de
  chaque caractère : `alignHan`, un 儿 collé en …r partage celle d'avant),
  boutons `[data-say]` « Mot » et `[data-say-ex]` « Phrase », ou « Écouter » seul sans exemple), bandeau 例
  (`slipHTML`, `renderSlip`, `revealSlip` ; en révision il montre la phrase en caractères et, sous
  « Traduction », sa traduction seulement ; la fiche du mot, mode `full`, y ajoute le pinyin), vues `study`/`words`/`progress`/`display`/`settings`,
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
  `#eval-go`/`#free-go`, `#eval-info`, `#forecast` (7 jours). Affichage (`renderDisplay`, `setLook`) : `#themes`
  (`THEME_NAMES`, nuancier `.swatch` dont chaque `.swp[data-swatch]` prend les jetons de son thème), `#look-sample` (aperçu :
  `cellsHTML`, `pinyinHTML`), choix `.seg.opt[data-look] [data-v]` et interrupteurs `.switch[data-look]` (un seul écouteur
  sur `#view-display` ; `data-look="tones"` : `none` coupe `toneColors` ; `#themes` dessiné une fois, le focus y reste ; la carte
  n'est redessinée que si `cardLook()` change ; une police absente de l'appareil, `fontHere` : son choix désactivé, `#zh-note`),
  `#sw-exform`, `#sw-ex`, `#tone-legend` (venus de
  Réglages › Cartes, devenu Voix). Pinyin en chiffres : `sylHTML`/`sylGap` (pour `pinyinHTML` et `markPinyin` : sans marque
  de ton, chiffre après la syllabe, rien pour le ton neutre, syllabes séparées). Taille du texte : toutes les tailles en
  px du `<style>` sont écrites `calc(Npx * var(--tz,1))` (`max(16px, …)` pour les champs), sauf l'en-tête et le menu ;
  `fit()` et `fitSlip` multiplient leurs tailles de départ par le facteur. Grille : `cellsHTML` met dans chaque case un
  `svg.mzg` (diagonales du 米字格). Réglages (`renderSettings`) :
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
  (`SHARED`) et `importShared` crée une liste du téléphone. Réglages : listes rangées par `deckGroupsHTML` (`DECK_GROUPS`, `listGroup` : HSK 2.0, HSK 3.0, chacune par niveau, autres
  listes figées, « Mes listes » avec les mots sans liste), `deckRowHTML` (interrupteurs
  `.switch[data-deck]` Réviser et `.switch[data-show]` Afficher), `freeRowHTML` (mots sans liste).
  Mots : filtres `data-f` (`new` = `inPass`, `known` = seau ≥ max(1, dernier − 1)), `meterHTML`, `knHTML`
  (形音义 allumés selon `kn`, aussi sous la carte et dans `#kn-counts` de Progrès), `knText` (fiche du mot).
  Progrès : sections Apprentissage (`#learn-go` caché tant qu'un apprentissage est enregistré, `#learn-info`, `#learn-box`,
  `#learn-hist` : `renderLearnHist`, les cinq derniers apprentissages finis puis les autres repliés, chacun s'ouvre sur ses
  mots) et Sens connus (`#kn-counts`, `#sens-go`, `#sens-info`) ; écran de fin : `#learn-start` ou `#done-learn`.
  `renderLearnStart` : `learnBtnsHTML` dans `#done-learn` et `#learn-box` (`data-learn` = `resume`, `drop`, confirmation
  `drop-yes`/`cancel`). Un seul bouton principal (`resumeLead`) : ce qui vient d'être mis en pause, sinon
  l'apprentissage, sinon le test, sinon `#done-back` ou `#eval-go`.
- **Écran d'ordinateur** (900 px de large et 500 de haut au moins : `WIDE = matchMedia(...)`, bloc CSS « computer screen » à
  la fin du `<style>` ; en dessous, et pour un téléphone couché, rien ne change) : `.app` en grille, `.top` en `display:
  contents` (`.brand` en haut du menu, `.top-r` compteurs et ＋), `.tabs` en menu à gauche (placé avant `<main>` dans la
  page pour l'ordre de tabulation, `order: 1` le garde en bas sur téléphone) ; révision : `#study-card` en grille (carte à
  gauche, `.status`, `#example`, `#actions` et `.keys` à droite), `studyRoom` ne retire que `.startface`, carte jusqu'à
  1100 px de large (sa colonne de la grille, 1116 px) et de la hauteur de la fenêtre (`maxW(room)` fonction, `room` = ce que
  rend `fill`, calculé une fois par `layout()`), `fit()` agrandit cellules, textes et boutons (`--ks`) avec `k` (rapport à
  `CARD_W` = 380, la largeur sur téléphone ; 1 sur téléphone) et réduit chaque texte trop grand par `shrink` (par moitiés :
  la taille que trouvait la boucle pas à pas, en quelques mises en page), la perspective de `.stage` suit `--pk` (largeur /
  `CARD_W`, posé par `layout()` ; sinon les faces de côté débordent ; `perspective: 1150px` d'abord pour un moteur sans
  `max()`) ; largeurs en variables sur `.app` : `--nav` (menu), `--side` (feuille), `--dock` (place prise par la fiche à côté
  de la liste) ; feuilles ouvertes à droite (`.panel`) ; la fiche du mot (`openSheet(…, beside)` : l'id du mot, seule
  `wordSheet` le donne) se range à côté de la liste dans Mots (`current`) si la fenêtre fait 1200 px (`DOCK`) : `setDock(id)`
  (`sheetWord`, `.sheet.dock`, `.app.docked` qui réduit `.app` de `--dock` : la barre de défilement de `main` reste visible ;
  sans voile ni `aria-modal`, ligne du mot marquée `aria-current`, le focus reste dans la liste, sur cette ligne si un clic
  ne l'y a pas mis, Safari) ; `showView` la ferme, `DOCK` qui ne tient plus la remet sous un voile (`setDock(null)`, le
  focus va dans la feuille). Progrès et Réglages en colonnes de 460 px
  (`column-width` ; groupes de Réglages en `<section class="sgroup">`), Mots en colonnes à partir de 1500 px. Un clic de
  souris sur un bouton de la révision (`#view-study`, écouteur à la capture : certains boutons arrêtent le clic) lui retire
  le focus (Espace tourne de nouveau la carte) ; Espace ou Entrée sur l'entrée courante du menu tourne la carte, sur une
  autre l'ouvre ; sans carte à l'écran (`#study-card` caché : écran de fin, chargement), les touches ne font rien.
- **Caractère dessiné** (Mots, crayon `#draw-open`, `#drawpad`) : `shapeOf(strokes)` (forme d'un dessin sans ordre des
  traits : grille `SHAPE_G` × `SHAPE_G` × 4 orientations, longueur de trait par case, autour du centre de gravité de l'encre et
  à l'échelle de son étalement, flou, racine, longueur 1), `loadShapes()` (formes des ~3 040 caractères de `traits/`, médianes,
  paquet par paquet dans `shapePacks`, gardés ; les paquets lus par `traitPack(n, false)`, sans rester en mémoire ;
  `shapesReady`, `shapesMissing` : un paquet absent est redemandé quand la case se rouvre, `padOpen` ; tout est refait quand
  `traits/` change de version), `guessChars(S, strokes, k)` (les k plus proches au cosinus, petite pénalité par trait de plus
  ou de moins ; un trait sans longueur compte comme un point). Réglages choisis sur les médianes déformées, mélangées,
  retournées et liées : `test_dessin.py` mesure le résultat (le bon caractère premier, ou parmi les dix). Case `pad` en SVG
  (`#pad` : une `polyline` par trait, en fractions de la case, à l'encre du thème ; `strokes`, `cur`, `id` : un seul doigt à
  la fois, un `pointercancel` n'en laisse rien ; `seq`/`shown` : dernière proposition affichée), `padDraw`, `padGuess`
  (« Chargement… » tant que les formes ne sont pas prêtes), `padClear`, `padOpen`, `bindPad`. Un caractère touché remplace
  dans `#q` ce qui n'est pas en caractères et s'y ajoute (`searchAdd`, `renderWords`), la case se vide, le message le dit (au clavier, le
  focus revient sur la case). La case suit la grille d'Affichage (`.pad-box`, `svg.mzg`). `traitPack` abandonne une
  requête au bout de 20 s.
- **Caractère par sa clé** (Mots, bouton `#keys-open` 部, `#keypad`) : `CLES` (ligne écrite par `outils\cles.py` : `[numéro
  du Kangxi (' : forme simplifiée), formes montrées (la première en grand), traits de la clé, {traits du caractère : caractères}]`,
  triée par traits de la clé), `keysRender(at)` (pose `keyAt` ; null : les clés, une ligne `.kgroup` par nombre de traits
  (marque `.kt`, clés dans `.kkeys`), 阝 « 右 »/« 左 » ; sinon les caractères de la clé, `#keys-list.chars`, une ligne
  `.kline` chacun par `keyCharHTML` (règles communes avec `.wrow`, sans le mode compact ; `content-visibility` : les lignes
  cachées ne sont pas mises en page) : caractère, lectures (celles du mot qu'il fait seul d'abord, puis les plus fréquentes
  dans les mots qui le contiennent, syllabe par `alignHan` : un 儿 collé en …r n'en a pas, 这儿 zhèr donne zhè ; un ton venu
  du mot, neutre ou de 一/不 (`TONELESS`), n'est pas montré à côté de la même syllabe avec le sien ; sans majuscule), sens de
  ce mot seul pour la première lecture (`senses`, `zhWrap`), sinon les mots les plus courts qui le contiennent, nombre de
  traits ; du moins au plus de traits, les plus employés d'abord ; en colonnes sur l'ordinateur ; seulement les clés et
  caractères des mots de `DECK`), `keysOpen` (la case
  de dessin se ferme : un panneau à la fois), `bindKeys`. Un caractère choisi passe par `searchAdd` (comme un dessiné), puis
  les clés reviennent. Dessin : `guessChars(…, 50)` dans `pad.top`, `pad.n` montrés (10, puis 10 de plus par `#pad-more`).
- **Ordre des traits** (fiche du mot, `#sheet-traits`) : `renderTraits(el, mot)` (chaque caractère CJK une fois),
  `strokesOf(ch)` / `traitPack(n)` (mémoire, puis cache `traits-xingyinyi`, puis réseau), `traitHTML` (grande case avec
  la ligne médiane de chaque trait découpée par son contour, `.ta` ; une case par étape, `use.t-done`/`t-new`/`t-todo`),
  `traceTraits` (« Animer » : `strokeDashoffset` trait après trait, rien si mouvement réduit), `prefetchTraits` (5 s
  après le démarrage, en ligne : les 32 paquets, de nouveau quand `index.json` change de version).
- **Synchronisation des appareils** (Réglages › `#sync-box`, `renderSync`, `renderSyncStatus`, `syncJoin`, `copiesSheet`) :
  `docOf(state)` donne le document partagé (pris comme après un rechargement, `normalizeState` : ce qu'il complète n'est pas
  un changement ; tout sauf `DEVICE_SETTINGS` = `autoAudio`, `rate`, `theme`, `textSize`, `motion`, `compact`, `zhFont`, et sauf la `pause` de l'apprentissage (`sansPause`), le jeton GitHub ; `custom`, `lists`,
  `learnLog` (par `start`) en maps par id ; `listsAt`), `stateFromDoc` l'inverse (un champ absent du document, version
  d'avant ou copie du serveur, garde celui de l'appareil ; un apprentissage venu d'ailleurs est en pause ici), `applyDoc` l'applique (`recomputeDue` si les délais changent, `mergeTel`,
  `afterDeckChange`). `mergeDocs(base, ici, serveur)` : `mergeMap` (une clé changée d'un seul côté prend ce côté, même plus
  bas, suppression comprise ; changée des deux côtés : la règle de la collection, même à valeur égale), `mergeCard` (la
  progression la plus avancée, `cardAhead` : seau, puis `d`, `t`, `r` ; `r` et `l` additionnés depuis la base ; remise à zéro
  d'un côté et révision de l'autre : la carte reste), `mergeDay` (historique additionné), réglages absents d'un document (version d'avant) comptés à leur valeur de `DEFAULTS`, `mergeSet` (ids des listes : ajout
  ou retrait d'un côté), apprentissage et test (`run` : changé d'un seul côté, ce côté ; des deux, `learnBoth`, le plus
  avancé : dernier passage, puis tour, puis moins de mots restants, puis `at`, ou `testBoth`, toutes les réponses gardées,
  celles d'ici d'abord, et les mots que personne n'a passés ; le côté qui a déjà toutes les réponses de l'autre est pris
  tel quel, sinon deux fenêtres s'échangeraient l'ordre sans fin ; deux `start` différents : `laterRun`, le plus récent ;
  abandonné d'un côté et avancé de l'autre : il reste, sauf si son `start` est dans `ended`, union des deux côtés),
  `learnLog` (union, `capLog`), un champ absent d'un document (version d'avant) compté comme inchangé (`field`),
  réglages : ceux de l'appareil qui fusionne ; sans base (premier code sur un appareil) : maximum,
  union, réglages du côté le plus avancé. `syncNow` : sans changement ici, `GET ?have=v` ; sinon `PUT {v de la base}` ; un 409
  apporte le document du serveur, fusion, nouvel envoi ; les changements faits pendant l'échange restent (`mergeDocs(local, now,
  …)`) ; `checkDoc` refuse un document d'une version plus récente (`SYNC_FMT`, `SCHED`). `syncSoon(ms, dirty)` (jamais plus
  tard qu'une synchronisation déjà prévue) : `save()` (20 s), démarrage (`useLists` « first »), retour au premier plan,
  réseau retrouvé ; mise en arrière-plan : tout de suite si un changement attend. `listsBehind()` (un autre appareil a des
  listes de decks/ plus récentes, `listsAt`) : `mergeTel` ne retire pas les ids inconnus ni les `listEdits`, `dropSameEdits` et
  `syncDeckSettings` attendent, et l'appli relit ses listes. `SYNC_URL` : adresse du serveur, https://xingyinyi-sync.guillaume-plehar.workers.dev
  (vide : champ dans Réglages ; `test_sync.py` la remplace par le serveur local dans ses copies du site). Ordinateur : `beforeinstallprompt` → `#install-row` « Installer sur cet ordinateur » ; carte plus grande
  (`maxW` de `Prism` peut être une fonction). Revue : `codeKey` (seuls lettres
  et chiffres du code comptent ; un code tapé inconnu du serveur demande « Créer ce code », sauf celui de `syncMade`),
  `renameDoc` (les renommages `moved` appliqués à la base et aux deux côtés avant la fusion), `still()` (« Arrêter » ou un
  autre code pendant l'échange : rien n'est réécrit), `reloadState` (une autre fenêtre a enregistré : écouteur `storage`,
  `lastSaved`, et au début de `syncNow`), `listsSig`/`listsH` (empreinte du contenu des listes : `listsBehind` exige un
  contenu différent et plus récent ; `noteLists` avant `applyDoc`), `tel` fusionné en trois voies (ordre stable),
  `followShared(before)` (après `applyDoc` et `reloadState`, avant `afterDeckChange` : l'apprentissage ou le test à l'écran
  suit l'état ; fini ou abandonné ailleurs : retour à la file avec un toast ; `study.res` relié au nouveau `state.test`),
  `reloadState` garde, pour l'apprentissage ou le test à l'écran, le plus avancé des deux fenêtres (une fenêtre d'une
  version d'avant, état sans `learnLog`, ne touche ni à eux ni à l'historique) ; `showDone` ne remonte le défilement que
  dans Réviser, et `followShared` ne redessine un écran de pause que s'il a changé, manifeste `launch_handler` focus-existing. Serveur : versions = heure en ms
  (jamais réutilisées), `MAX_CODES` (5 par défaut, 403 au-delà), documents de 1 Mo au plus.
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
  guillemets « », nombre et nom liés par une espace insécable (`plural`). Les listes de `decks/` écrivent
  souvent une espace ordinaire : sens, note et traduction de l'exemple passent par `frTypo` à l'affichage
  (`senseItems`, note de la face 义, `slipHTML`, `wordRowHTML`), jamais dans les données.
- Couleurs des tons (`--t1` rouge, `--t2` orange, `--t3` bleu, `--t4` violet, `--t5` gris ; Pleco et MDBG par
  `[data-tones]`, clairs ou sombres selon `[data-mode]`, plus foncés pour Sépia et Contraste élevé), thèmes par jetons CSS : `:root` (Cahier, cahier d'écolier),
  `prefers-color-scheme` sur `:root:not([data-theme])` (Tableau noir automatique), un bloc `:root[data-theme="…"]` par thème
  (`dark` tableau noir, `paper`, `sepia`, `contrast`, `night`), chacun aussi pour `[data-swatch="…"]`. Toute nouvelle couleur
  passe par un jeton défini dans chacun de ces blocs ; texte courant (`--ink`, `--pencil`, `--faint`, `--accent`, tons de chaque
  palette) d'au moins 4,5 : 1 sur `--page` et `--bg` (`--grid` et `--pen` : traits, cadres, marques).
- Polices : `--zh` (WenKai, `--zh-kai` ; `--zh-hei` et `--zh-song` selon Affichage, polices de l'appareil) pour le chinois,
  `--ui` (Andika : a et g à une boucle, comme à l'école) ; le nom de l'appli reste en WenKai. Une taille de police passe par
  `calc(Npx * var(--tz,1))` (taille du texte), sauf dans l'en-tête et le menu.
  Un mot dont un caractère manque à la police prend la classe `.sysfont` (`covered()`).
- Phrases d'exemple : contenant le mot, avec les seuls caractères du niveau du mot ou en dessous (HSK 1-3 pour
  `decks/hsk1-3.tsv`, `outils/caracteres_hsk1-3.txt` ; `outils/hsk/controle.py` pour les autres) ; pinyin des manuels
  (tons neutres, 一 et 不 avec leur ton réel, 儿 collé).
- iPhone : pas de `alert`/`confirm`/`prompt` (confirmations dans la page), champs en 16 px au moins
  (sinon Safari zoome), zones de sécurité `env(safe-area-inset-*)`, cibles tactiles d'au moins 34 px,
  animations réduites respectées (`[data-motion="reduce"]` en CSS, `reducedMotion()` en JS : l'appareil ou Affichage).
- JavaScript sans dépendance ni bibliothèque externe, dans `index.html`. Pas de `console.log` laissé.
- Messages et sorties des outils Python en UTF-8 (ils forcent `reconfigure`) ; commandes affichées en
  syntaxe Windows (`py outils\…`).

## Vérifier un changement

1. `py tests\test_seance.py` (dont l'écran d'ordinateur, 1366 × 768), `py tests\test_seaux.py`, `py tests\test_listes.py`, `py tests\test_dico.py`, `py tests\test_affichage.py`, `py tests\test_dessin.py` et, si la
   synchronisation change, `py tests\test_sync.py` et `node tests\test_serveur_sync.mjs` ; ajoute un test
   pour toute nouvelle fonction. Tout changement du planning (seaux, file, évaluation, migration)
   passe par `tests/test_seaux.py`.
2. Regarde le résultat : captures dans `tests/sortie/captures`, ou `py -m http.server 8000` avec les
   outils de développement du navigateur en mode iPhone (390 × 844), en clair et en sombre.
3. Si le format des cartes ou du planning change encore : incrémente `SCHED` et écris la migration
   dans `normalizeState` (les sauvegardes restaurées y passent aussi).
4. `py outils\version_appli.py`, mise à jour de `LISEZMOI.md` si l'usage change, puis commit et push.

## Idées en attente

- Ordre des listes (donc du premier tour) modifiable depuis le téléphone.
