# 形音义 : flashcards HSK à trois faces

Chaque carte est un prisme à trois faces : 形 le caractère, 音 le pinyin, 义 le sens en français.
Une fois la carte tournée, une phrase d’exemple (例) apparaît dessous, écrite avec les seuls
caractères des niveaux 1 à 3, avec sa traduction à la demande ; son pinyin est sur la face 音,
où tu peux aussi l’écouter.

L’appli tourne sur l’iPhone, hors ligne, depuis l’écran d’accueil. Les listes de mots vivent dans
ce dossier, sur ton ordinateur : tu les modifies, tu publies avec git, et le téléphone se met à jour
tout seul. Ta progression, elle, reste sur l’appareil, ou passe d’un appareil à l’autre si tu les
synchronises (section 7). L’appli s’installe aussi sur l’ordinateur.

Ce que contient le dossier :

| Élément | Rôle |
|---|---|
| `index.html`, `sw.js`, `manifest.webmanifest`, icônes | l’appli |
| `decks/` | les listes de mots : c’est là que tu ajoutes et corriges des mots |
| `decks/decks.json` | la liste des listes : nom, fichier, active ou non ; leur ordre est celui du premier tour |
| `outils/decks.py` | vérifier une liste, ajouter un mot, compléter le pinyin |
| `fonts/` | polices LXGW WenKai et Andika (licence libre, voir `fonts/OFL.txt`) |
| `CLAUDE.md`, `tests/`, `outils/version_appli.py` | pour faire évoluer l’appli avec Claude Code (section 9) |

Listes fournies : HSK 1 à 6 (2.0), les listes officielles HSK 2.0 de 2012, celles de l’examen de
novembre ; HSK 1 à 6 (3.0), le programme d’examen HSK 3.0 de 2026 ; Perso (vide, pour tes mots).
HSK 1 à 3 (2.0) sont actives au départ, les autres attendent dans Réglages (section 5). Les fiches
des listes HSK 4 à 6 et HSK 3.0 ont été rédigées puis relues une à une.

**Un mot n’existe qu’une fois** dans le dictionnaire (mêmes caractères, même pinyin, même sens) et
appartient à toutes les listes qui le contiennent : 爱 est dans HSK 1 (2.0) et dans HSK 1 (3.0),
avec une seule carte et une seule progression. Deux mots qui s’écrivent pareil mais se lisent
autrement (还 hái, 还 huán) ou n’ont pas le même sens (点 diǎn « heure », 点 diǎn « commander ») sont
deux mots. Les listes HSK sont figées ; tes listes à toi peuvent contenir des mots HSK et des mots
nouveaux.


## 1. Installation (une seule fois)

### 1.1 Préparer l’ordinateur

Il te faut un compte GitHub gratuit (https://github.com/signup), git et, pour se connecter
facilement, l’outil `gh` de GitHub.

**Sur Mac**, ouvre le Terminal (Applications › Utilitaires) :

```sh
git --version          # si git manque, macOS propose de l’installer : accepte
brew install gh        # si tu as Homebrew ; sinon télécharge gh sur https://cli.github.com
```

**Sur Windows**, installe Git for Windows (https://git-scm.com) et utilise le terminal « Git Bash »
pour toutes les commandes de ce guide. Puis : `winget install --id GitHub.cli`.

Si c’est la première fois que tu utilises git sur cet ordinateur, présente-toi :

```sh
git config --global user.name "Guillaume"
git config --global user.email "ton-adresse@exemple.fr"
```

### 1.2 Mettre le dossier sous git

Décompresse `xingyinyi-appli.zip` (double-clic) et range le dossier `xingyinyi` où tu veux le
garder, par exemple dans Documents. Puis :

```sh
cd ~/Documents/xingyinyi
git init -b main
git add .
git commit -m "形音义 : première version"
```

### 1.3 Créer le dépôt sur GitHub et l’envoyer

```sh
gh auth login
```

Réponds : GitHub.com, HTTPS, « Authenticate Git with your GitHub credentials » : Yes,
« Login with a web browser ». Un code s’affiche ; colle-le dans la page qui s’ouvre. Ensuite :

```sh
gh repo create xingyinyi --public --source=. --remote=origin --push
```

Le dépôt est créé et tes fichiers sont envoyés.

> Sans `gh` : crée un dépôt vide sur https://github.com/new (nom `xingyinyi`, Public, sans
> README), puis `git remote add origin https://github.com/TON-IDENTIFIANT/xingyinyi.git` et
> `git push -u origin main`. Quand git demande un mot de passe, il faut un jeton d’accès
> (Settings › Developer settings › Personal access tokens) : c’est pour ça que `gh` est plus simple.

### 1.4 Publier avec GitHub Pages

Sur github.com, dans le dépôt `xingyinyi` : **Settings › Pages**, rubrique « Build and deployment » :
Source « Deploy from a branch », branche `main`, dossier `/ (root)`, puis **Save**.

Ou, depuis le Terminal, dans le dossier :

```sh
gh api -X POST "repos/{owner}/{repo}/pages" -f "source[branch]=main" -f "source[path]=/"
```

Une à deux minutes plus tard, l’appli est en ligne à l’adresse
`https://TON-IDENTIFIANT.github.io/xingyinyi/` (elle s’affiche aussi dans Settings › Pages).

Le dépôt doit rester public : c’est la condition de GitHub Pages gratuit. Les listes de mots sont
donc visibles par qui connaît l’adresse ; ta progression, elle, n’est jamais envoyée sur GitHub.

### 1.5 Installer sur l’iPhone

1. Ouvre l’adresse dans **Safari**.
2. Bouton Partager (le carré avec une flèche) › **Sur l’écran d’accueil** › Ajouter.
3. Lance l’appli une première fois depuis l’icône, avec du réseau : elle télécharge les listes
   et les polices. Ensuite elle marche aussi hors ligne.

Ouvre-la toujours depuis l’icône : l’appli de l’écran d’accueil garde sa propre progression,
séparée de Safari.

Pour la voix : Réglages de l’iPhone › Accessibilité › Contenu énoncé › Voix › Chinois (mandarin),
et télécharge une voix de bonne qualité.


## 2. Sur l’iPhone, au quotidien

- **Réviser** : touche la carte ou fais-la glisser pour la tourner. La face 形 montre déjà la
  phrase d’exemple en caractères, la face 音 la montre en pinyin (réglable) ; sur 音, **Mot** et
  **Phrase** lisent à voix haute le mot ou la phrase ; sur 形, **Traits** trace les caractères trait par
  trait dans leurs cases (touche de nouveau pour revoir le tracé) et **Décomposer** ouvre en bas chaque
  caractère décomposé, une case par trait. Dès que la carte a tourné, la phrase en
  caractères se découvre sous la carte (例) ; « Traduction » affiche sa traduction. Pendant la révision, le pinyin de
  la phrase n’est que sur la face 音 ; la fiche du mot (onglet Mots) montre tout.
  Note-toi ensuite : × **Raté** ou √ **Réussi** (au clavier : 1 et 2). Sous chaque bouton, l’appli
  écrit où ira le mot, par exemple « seau 0, fin de file » sous × et « seau 2, 3 jours » sous √.
  Sous la carte, une étiquette indique « Nouveau mot » ou le seau du mot.
  Le haut de l’écran compte les mots **à voir** (pas encore passés au premier tour) et les mots
  **à revoir** (ratés, ou dont le délai est écoulé). Comment avance la file : section 5.
- **＋** (en haut à droite, depuis n’importe quel écran) : créer une nouvelle fiche tout de suite.
- **Mots** : le dictionnaire. L’onglet **Toutes** montre, une seule fois chacun, les mots des
  listes que tu as choisi d’afficher (Réglages › Listes › Afficher), puis les mots qui ne sont dans
  aucune liste ; un onglet par liste, et **Sans liste**. La recherche (caractères, pinyin sans
  accents ou français) parcourt tout le dictionnaire, listes masquées comprises. Filtres
  d’avancement : À voir, En cours, Acquis (les deux derniers seaux). La fiche d’un mot indique ses
  listes, son seau et sa prochaine révision ; **Listes…** l’ajoute à une de tes listes ou l’en retire.
  En bas, l’**ordre des traits** de chaque caractère : une case par trait, le nouveau en couleur, et
  **Animer** pour voir le caractère se tracer. Ces données (3 Mo environ) se téléchargent une fois,
  en arrière-plan, puis restent sur le téléphone, hors ligne compris.
  Si la recherche ne trouve rien, **Créer la fiche « … »** ouvre le formulaire déjà rempli avec ce
  que tu as tapé.
- **Progrès** : mots passés, en tout et par liste, ce qu’il reste à voir au premier tour et quand
  il sera fini à ton rythme, le rythme à tenir avant l’examen, le nombre de mots dans chaque seau
  et les révisions prévues sur la semaine. C’est aussi là que tu lances un **apprentissage**, une **évaluation**, un
  **test complet**, un test **nouveau sens** ou un **entraînement libre** (section 5).
- **Réglages** : les listes rangées en HSK 2.0, HSK 3.0 et Mes listes ; pour chaque liste, **Réviser** (elle entre dans la file) et **Afficher** (ses mots
  apparaissent dans Mots › Toutes) ; seaux et délais, nombre de mots par apprentissage et par évaluation, date de l’examen,
  publication sur GitHub, affichage des cartes et voix, mise à jour de l’appli (Appli › Vérifier),
  sauvegarde.

Le premier tour suit l’ordre des listes actives : d’abord celles créées sur le téléphone (dont
« Ajoutés ici »), puis Perso, HSK 3, HSK 2 et HSK 1, dans l’ordre de `decks/decks.json`. Dans
chaque liste, les mots arrivent dans l’ordre des lignes du fichier (pour les listes HSK : du plus
fréquent au plus rare). Un mot de deux listes actives ne passe qu’une fois, avec la première.


## 3. Ajouter ou corriger des mots depuis l’ordinateur

### Le format des listes

Chaque fichier `decks/*.tsv` contient un mot par ligne, colonnes séparées par une **tabulation** :

| Colonne | Contenu | Obligatoire |
|---|---|---|
| hanzi | le mot en caractères ; il sert d’identifiant | oui |
| pinyin | `túshūguǎn` ou `tu2shu1guan3` ; deux lectures : `zhǐ / zhī` | oui |
| francais | les sens, séparés par `;` | oui |
| note | remarque affichée sous les sens | non |
| audio | ce que la voix lit si le mot seul se lit mal (`还书` pour 还 huán) | non |
| exemple | phrase en caractères contenant le mot | non |
| exemple_pinyin | pinyin de la phrase | non |
| exemple_fr | traduction de la phrase | non |

Une ligne **sans traduction** ne crée pas de mot : elle renvoie à un mot défini dans une autre
liste. Pour mettre 图书馆 du HSK 3 dans ta liste Perso, écris seulement `图书馆` ; si plusieurs mots
s’écrivent ainsi, ajoute le pinyin (`还	huán`) ; pour deux homographes de même pinyin, écris
l’identifiant du mot (`hsk30-2:点`). `verifier` signale un renvoi qui ne mène à rien, et un mot
défini deux fois.

Les lignes qui commencent par `#` sont des commentaires. Un éditeur de texte comme VS Code (ou
TextEdit, qui ouvre ces fichiers en texte brut) convient. Évite Excel : en enregistrant, il abîme
souvent les caractères chinois. Si ton éditeur remplace les tabulations par des espaces, l’appli
s’en sort quand même, `verifier` te le signale et `completer` remet des tabulations.

### Le plus simple : la commande `ajouter`

Une fois pour toutes, installe le calcul automatique du pinyin :

```sh
python3 -m pip install pypinyin
```

(Sous Windows : `py` au lieu de `python3`.) Puis, depuis le dossier `xingyinyi` :

```sh
python3 outils/decks.py ajouter 打印 "imprimer" --exemple "我要打印这张照片。" --traduction "Je dois imprimer cette photo."
```

Le mot est ajouté à la fin de `decks/perso.tsv`, avec le pinyin du mot et celui de la phrase
calculés (relis-les : les caractères à plusieurs lectures demandent un coup d’œil). Pour une autre
liste : `--liste hsk3`. Pour donner le pinyin toi-même : `--pinyin da3yin4`.

Si tu as écrit des lignes à la main sans pinyin :

```sh
python3 outils/decks.py completer decks/perso.tsv
```

### Vérifier, puis publier

```sh
python3 outils/decks.py verifier
git add decks
git commit -m "Nouveaux mots"
git push
```

`verifier` signale les colonnes manquantes, les doublons, le pinyin mal formé (une apostrophe
oubliée dans `xī'ān`, par exemple), les phrases qui ne contiennent pas le mot et les caractères
d’exemple hors HSK 1-3.

Sur l’iPhone, attends une à deux minutes (le temps que GitHub publie), puis ouvre l’appli : elle
récupère les listes toute seule et affiche ce qui a changé (« Perso : 3 mots ajoutés »). Pour
forcer la vérification : Réglages › **Chercher une mise à jour des listes**.

### Corriger un mot

Modifie sa ligne dans le fichier et publie. Changer le pinyin, le français ou l’exemple garde la
progression du mot. Changer la colonne hanzi crée un nouveau mot (l’ancien disparaît des
révisions). Supprimer une ligne retire le mot ; si tu le remets plus tard, il retrouve sa progression.

Tu peux aussi corriger un mot sur le téléphone (Mots › le mot › Modifier) : la correction reste sur
le téléphone et prend le pas sur la liste. Reporte-la dans le fichier pour la garder partout.


## 4. Listes et mots créés sur le téléphone

### Créer, remplir, supprimer une liste

- Mots › **＋ Nouvelle liste** : donne-lui un nom (« Cours du mardi »). Elle s’ouvre aussitôt.
- Dans une liste du téléphone : **Ajouter un mot ici**, **Partager la liste**, **Renommer**,
  **Supprimer la liste** (ses mots restent dans le dictionnaire, avec leur progression).
- Le formulaire **Ajouter** (ou le bouton **＋** en haut de l’écran) a aussi un champ « Liste »,
  avec « Aucune liste » et « Nouvelle liste… ». Si le mot tapé est déjà dans le dictionnaire, le
  formulaire le montre avec **Ajouter celui-ci à la liste** : un mot n’est jamais écrit deux fois.
- Un mot HSK entre dans une de tes listes par sa fiche (Mots › le mot › **Listes…**). Les listes
  HSK, elles, ne changent pas ; Perso et les listes du dépôt qui ne sont pas HSK peuvent aussi
  recevoir des mots depuis le téléphone (en attente de publication).

Les listes du téléphone passent en tête du premier tour. Tant qu’elles ne sont pas publiées,
elles n’existent que sur ce téléphone.

### Publier depuis le téléphone, sans l’ordinateur

L’appli peut écrire elle-même dans ton dépôt GitHub : chaque liste du téléphone devient un fichier
`decks/<nom>.tsv` déclaré dans `decks.json`, les mots de « Ajoutés ici » vont dans `perso.tsv`, les
mots ajoutés à Perso ou retirés y sont reportés, les mots sans liste vont dans `mots.tsv`, et les
corrections faites sur des mots HSK sont reportées dans leur fichier. Un mot HSK n’y est écrit
qu’en renvoi (ses caractères). La progression est gardée. Il lui faut un **jeton d’accès** limité
à ce dépôt :

1. Sur github.com : avatar › **Settings** › **Developer settings** › **Personal access tokens** ›
   **Fine-grained tokens** › **Generate new token**.
2. Nom : `xingyinyi téléphone` ; expiration : un an ; **Repository access** : « Only select
   repositories » › `xingyinyi`.
3. **Permissions** › Repository permissions › **Contents** : « Read and write ». Rien d’autre.
4. **Generate token**, puis copie le jeton (`github_pat_…`) ; il ne s’affiche qu’une fois.
5. Dans l’appli : Réglages › **Publier depuis le téléphone** : le dépôt est déjà rempli, colle le
   jeton, **Connecter**.

Ensuite, **Publier sur GitHub** (dans Réglages, ou sous la liste de mots) envoie tout en un seul
commit. Avec le jeton, chaque liste des Réglages a aussi un bouton **Supprimer** qui la retire
du dépôt.

Le jeton reste dans l’appli, sur ce téléphone ; « Déconnecter » l’efface. S’il fuit, il ne donne
accès qu’au contenu de ce dépôt, et tu peux le révoquer sur la même page de GitHub.

**Important** : après une publication depuis le téléphone, lance `git pull` sur l’ordinateur
avant de modifier les listes, sinon `git push` sera refusé.

### Sans jeton

Mots › **Copier pour l’ordinateur** donne, pour chaque liste du téléphone, les lignes à coller et
le fichier où les mettre : `decks/perso.tsv` pour « Ajoutés ici » ; pour une autre liste, un
fichier créé avec `py outils\decks.py nouvelle-liste <id> "<nom>"` (la commande exacte est
affichée). Lance ensuite `py outils\decks.py completer` sur le fichier, puis publie avec git. À la
mise à jour suivante, ces mots passent dans la liste du dépôt du même nom en gardant leur
progression. Un mot créé sur le téléphone et présent dans deux de tes listes n’est écrit en entier
qu’une fois (l’autre liste y renvoie), et les mots que la liste du dépôt a déjà ne sont pas
répétés. Un mot corrigé sur le téléphone après la copie garde ta correction quand sa ligne arrive.

Un mot peut figurer dans plusieurs listes (par exemple un mot du HSK 3 dans ta liste « Cours du
mardi ») : il garde une seule carte. Un mot créé sur le téléphone qui a les caractères et le
pinyin d’un mot HSK devient ce mot HSK, avec sa progression ; un mot de mêmes caractères mais d’une
autre lecture (行 háng à côté de 行 xíng) reste un mot à part.

Réglages › Listes › **Supprimer du dépôt** retire une de tes listes du dépôt GitHub. Si elle
définit des mots, ils restent dans le dictionnaire (sans liste), avec leur progression, et les
autres listes qui les contiennent les gardent.

### Partager une liste avec quelqu’un d’autre

Dans une de tes listes : **Partager la liste**. L’appli prépare un petit fichier texte (quelques
centaines d’octets pour une liste de cent mots HSK : seuls leurs caractères y sont écrits ; un mot
qui n’est pas dans les listes HSK y est écrit en entier) et ouvre le menu de partage de l’iPhone
(Messages, AirDrop, mail…). L’autre personne l’ouvre dans son appli avec Mots › **Importer des
mots** › le fichier : la liste arrive comme une nouvelle liste de son téléphone, les mots qu’elle a
déjà ne sont pas écrits deux fois. Un mot noté autrement est reconnu : yīqǐ pour yìqǐ, le pinyin
en chiffres (na3r pour nǎr), et péngyǒu pour péngyou quand le sens est le même (东西 dōngxī « est et
ouest » reste un autre mot que 东西 dōngxi « chose »). Parmi deux homographes (花 « dépenser »,
花 « fleur »), l’import prend celui dont le sens correspond, et le signale quand il ne peut pas
choisir. Le formulaire ＋ suit la même règle.


## 5. Les seaux et la file

### Les seaux

L’appli range chaque mot dans un **seau**. Au départ, il y en a 7, numérotés de 0 à 6, chacun
avec son délai de retour :

| Seau | Le mot revient |
|---|---|
| 0 | quand tous les mots qui le précèdent dans la file sont passés |
| 1 | 1 jour après |
| 2 | 3 jours après |
| 3 | 1 semaine après |
| 4 | 2 semaines après |
| 5 | 1 mois après |
| 6 | 2 mois après |

Tous les mots commencent au seau 0. √ (Réussi) fait monter le mot d’un seau : un mot du seau 2
réussi passe au seau 3 et revient une semaine plus tard. Au dernier seau, il y reste et revient
tous les 2 mois. × (Raté) renvoie le mot au seau 0, à la fin de la file, quel que soit son seau.

### La file

Les mots passent un par un, comme dans une file d’attente :

1. **Le premier tour** : d’abord tous les mots des listes actives qui ne sont pas encore passés,
   dans l’ordre des listes puis des lignes (section 2). Pas de quota par jour : tu avances à ton
   rythme, et le premier tour reprend où tu t’es arrêté.
2. **Ensuite** : les mots ratés et ceux des seaux 1 à 6 dont le délai est écoulé, dans l’ordre où
   ils sont arrivés dans la file (le plus ancien d’abord). Un mot à revoir y entre le jour de son
   échéance, un mot raté au moment du ×. Un mot raté se remet donc au bout de la file : il revient
   quand tous les mots devant lui sont passés, dans la même séance s’il le faut.

Un mot ajouté plus tard à une liste active passe lui aussi par le premier tour, avant les révisions.
Quand la file est vide, l’écran « File terminée » indique combien de mots reviendront demain.

**Pour te concentrer sur le HSK 3** : dans Réglages › Listes, coupe **Réviser** pour HSK 1 et HSK 2. Sinon le
premier tour passe aussi par leurs 301 mots avant que les révisions commencent. Tu pourras les
réactiver plus tard : leurs mots entreront alors dans le premier tour, devant les révisions,
jusqu’à ce qu’ils soient tous passés.

### Changer les délais et le nombre de seaux

Dans Réglages › Seaux :

- **−** et **+** raccourcissent ou allongent le délai de chaque seau, de 1 jour à 1 an.
- **Ajouter un seau** en crée un après le dernier, avec un délai environ deux fois plus long
  (10 seaux au plus, du seau 0 au seau 9).
- **Retirer le seau N** supprime le dernier seau (le 6 au départ) ; ses mots descendent dans le
  seau précédent. Il reste toujours au moins deux seaux.
- **Revenir aux 7 seaux d’origine** rétablit les délais du tableau ci-dessus.

Les dates de retour des mots déjà rangés sont aussitôt recalculées, à partir de leur dernière
révision.

### L’évaluation

Progrès › **Faire une évaluation** (le même bouton apparaît à la fin de la file) : un contrôle
de 20 mots (par défaut) tirés dans tous les seaux, à tour de rôle pour que chaque seau soit
représenté, puis mélangés. Seuls les mots déjà vus des listes actives y entrent. Un mot raté
retourne au seau 0, à la fin de la file, comme un raté ordinaire ; un mot réussi garde son
seau et sa date de retour.

À la fin, l’appli affiche ton score, le résultat seau par seau et les mots ratés. **Arrêter**
termine l’évaluation en cours et montre les résultats déjà obtenus ; **Reprendre la file** te
ramène aux révisions. Le nombre de mots se règle dans Réglages › Évaluation (de 5 à 100, de 5
en 5).

### L’apprentissage

Progrès › **Apprendre 20 mots** (le même bouton apparaît sur les écrans de fin) : l’appli tire
au hasard 20 mots du seau 0 des listes actives (mots jamais vus ou ratés ; le nombre se règle
dans Réglages › Apprentissage, de 5 à 50). Ils passent par **tours** : à chaque tour, chacun des
20 mots passe une fois, dans un ordre tiré au hasard. Si tu en as raté au moins un, un nouveau tour
recommence avec les 20 mots, dans un nouvel ordre. Les tours ne touchent pas à tes seaux.

Quand tu as réussi les 20 mots dans un même tour, un **dernier passage** pose chaque mot une fois :
un mot réussi passe au seau 1 (il revient demain), un mot raté reste au seau 0, à la fin de la
file. **Arrêter** pendant les tours ne change rien ; pendant le dernier passage, il montre les
résultats déjà obtenus. Si l’appli se ferme pendant un apprentissage (l’iPhone la ferme parfois en
arrière-plan), elle le reprend à la réouverture, là où tu l’avais laissé.

### Les sens connus

Un mot est connu **par le caractère**, **par le pinyin** ou **par la traduction** selon la face
d’où sa carte est partie quand tu l’as réussi (形, 音 ou 义 : c’est le réglage « D’abord » au-dessus
de la carte, ou le hasard). Un × lui fait perdre tous ses sens. Les sens connus s’affichent
dans la liste Mots (形音义, allumés quand le sens est connu), dans la fiche du mot, sous la carte
pendant la révision et dans Progrès › Sens connus. Les mots déjà au seau 1 ou plus avant cette
version comptent comme connus par la face de départ réglée à ce moment-là.

**Tester un nouveau sens** (Progrès › Sens connus) prend au hasard jusqu’à 20 mots (le nombre de
l’évaluation) connus dans un ou deux sens, et les pose dans chacun des sens qui leur manquent :
la carte part alors de la face à tester (le sélecteur « D’abord » la montre, sans changer ton réglage). Un √ ajoute ce sens sans toucher aux seaux ; un ×
renvoie le mot au seau 0, lui fait perdre tous ses sens, même ceux gagnés pendant ce test, et
retire ses autres sens du test Le bilan compte alors comme ratés les sens qu’il venait de gagner.

### Le test complet

Progrès › **Faire un test complet** (le même bouton apparaît sur les écrans de fin) : tu coches
les listes à tester (au départ, les listes actives ; cocher ici ne change pas les listes de la
file), puis l’appli te pose **tous** leurs mots, dans le désordre, y compris ceux que tu n’as
pas encore vus. Un mot raté retourne au seau 0, à la fin de la file ; un mot pas encore vu et
réussi passe directement au seau 1 (tu le connais déjà, inutile de le voir au premier tour) ;
les autres mots réussis gardent leur seau et leur date de retour.

Le test est enregistré après chaque réponse. **Pause** l’interrompt et montre les résultats
déjà obtenus ; tu peux le reprendre plus tard, même après avoir fermé l’appli, avec
**Reprendre le test** (dans Progrès ou sur les écrans de fin). **Abandonner le test** l’arrête
pour de bon : les réponses déjà données restent comptées. À la fin, l’appli affiche ton score,
le résultat seau par seau (« Nouveaux » pour les mots pas encore vus) et les mots ratés.

### L’entraînement libre

**S’entraîner librement** (dans Progrès ou à la fin de la file) mélange les mots déjà vus des
listes actives (tous leurs mots s’il y en a moins de 5) : tes réponses ne changent rien aux
seaux. Un mot raté revient à la fin de l’entraînement. **Arrêter** ramène à la file.


## 6. Ajouter une liste (par exemple le nouveau HSK 3.0)

```sh
python3 outils/decks.py nouvelle-liste hsk30-3 "HSK 3.0 niveau 3"
```

Cette commande crée `decks/hsk30-3.tsv` avec la ligne d’en-tête et inscrit la liste dans
`decks/decks.json`. Remplis le fichier, vérifie, publie. À la main, une liste se déclare ainsi
dans `decks/decks.json` :

```json
{ "id": "hsk30-3", "nom": "HSK 3.0 niveau 3", "fichier": "hsk30-3.tsv", "actif": true }
```

| Champ | Sens |
|---|---|
| `id` | identifiant court, à ne plus changer : la progression y est attachée |
| `nom` | nom affiché dans l’appli |
| `fichier` | fichier de la liste dans `decks/` |
| `actif` | `false` pour garder une liste hors de la file ; quand tu changes cette valeur, elle l’emporte sur l’interrupteur Réviser du téléphone |
| `afficher` | `false` pour ne pas montrer ses mots dans Mots › Toutes (par défaut : affichée) ; même règle face à l’interrupteur Afficher |
| `fixe` | `true` pour une liste que le téléphone ne modifie pas (les listes HSK) ; ses mots restent corrigeables |
| `dictionnaire` | `true` pour un fichier de mots qui ne sont dans aucune liste (`mots.tsv`) |

L’ordre des listes dans `decks.json` est l’ordre du premier tour (après les listes du téléphone).
Les champs `mode` et `parJour` des anciennes versions (listes de rappel, mots par jour) ne servent
plus : un ancien fichier peut les garder, l’appli les ignore et `verifier` te signale que tu peux
les enlever. Un mot n’est défini qu’une fois (dans la première liste qui le contient) ; les autres
listes y renvoient par une ligne sans traduction (section 3). Les listes HSK 4 à 6 et HSK 3.0 sont
produites par `outils/hsk/` (voir `outils/hsk/LISEZMOI.md`).


## 7. Sauvegarder, ordinateur, appareils synchronisés

### 7.1 Sauvegarder

La progression est enregistrée sur chaque appareil. Réglages › **Exporter un fichier** l’enregistre
dans Fichiers (iCloud Drive, par exemple) ; « Restaurer » la recharge. Supprimer l’icône de
l’appli supprime aussi sa progression : exporte d’abord, ou synchronise (7.3). Une sauvegarde faite
avant le passage aux seaux se restaure aussi, mais tous ses mots repartent du seau 0 (voir section 8).

### 7.2 L’appli sur l’ordinateur

Ouvre l’adresse de l’appli (`https://TON-IDENTIFIANT.github.io/xingyinyi/`) dans **Edge** ou
**Chrome**, puis Réglages › Appli › **Installer sur cet ordinateur** (ou l’icône « Installer » au bout
de la barre d’adresse). L’appli s’ouvre alors dans sa propre fenêtre, depuis le menu Démarrer,
marche hors ligne et se met à jour comme sur l’iPhone. Sur un écran large, les sections passent dans
un menu à gauche ; en révision, la carte s’agrandit et l’exemple et les réponses se rangent à côté ;
dans Mots, la fiche d’un mot s’ouvre à côté de la liste, qui reste utilisable ; Progrès et Réglages
tiennent sur deux colonnes. Une fenêtre étroite reprend la mise en page du téléphone. Au clavier :
**Espace** tourne la carte, **1** et **2** notent × et √, **A** lit le mot, **E** la phrase.

### 7.3 Synchroniser l’iPhone et l’ordinateur

Chaque appareil a sa propre progression. Pour retrouver la même partout, donne-leur un **code
commun** (Réglages › **Synchroniser les appareils**) :

1. Sur l’iPhone : **Créer un code** propose un code de quatre syllabes et un nombre (par exemple
   `lan-shu-qiao-mei-58`) ; note-le. Puis **Utiliser ce code** : ta progression part sur le serveur.
2. Sur l’ordinateur : tape le même code (seuls lettres et chiffres comptent : majuscules, espaces et tirets non),
   puis **Utiliser ce code** : l’ordinateur reçoit la progression de l’iPhone, fusionnée avec la sienne.

Un code tapé que personne n’utilise encore est d’abord à confirmer (« Créer ce code ») : vérifie-le,
une faute de frappe ferait une seconde progression partagée.

Ensuite, tout est automatique : chaque appareil envoie ses réponses une vingtaine de secondes après,
et dès que tu passes à une autre appli ; si tu fermes l’appli juste après une réponse, elle part à la
prochaine ouverture. Il reçoit les réponses des autres à l’ouverture et quand tu y reviens. Sans réseau, il attend et envoie tout au retour de la connexion. **Synchroniser
maintenant** force l’échange.

Ce qui passe d’un appareil à l’autre : la progression de chaque mot, l’historique de Progrès, les
mots, listes et corrections créés sur un appareil, les réglages (listes actives, seaux, nombres de
mots, date de l’examen…). Restent propres à chaque appareil : la voix (prononciation automatique,
vitesse), le jeton GitHub, un test ou un apprentissage en cours.

**En cas de conflit**, c’est-à-dire un mot travaillé sur les deux appareils entre deux
synchronisations, le mot garde sa progression **la plus avancée** (le seau le plus haut, puis la
révision la plus récente), et ses révisions s’additionnent. Un mot changé d’un seul côté prend
simplement ce côté, même s’il a été raté : rater un mot sur l’ordinateur le renvoie bien au seau 0
sur l’iPhone. Un réglage changé des deux côtés garde celui de l’appareil qui synchronise en second.

**Copies du serveur.** Le serveur garde une copie de la progression partagée par jour d’usage,
30 au plus. Réglages › Synchroniser les appareils › **Copies du serveur…** permet de revenir à l’une
d’elles, pour tous les appareils (ce qui a été fait depuis est perdu).

**Arrêter sur cet appareil** le détache du code : sa progression reste, celle du serveur aussi.
Attention : « Effacer toute la progression » et « Restaurer » valent pour tous les appareils
synchronisés ; pour repartir de zéro sur un seul, arrête d’abord la synchronisation sur celui-là.

Le code sert de clé : quiconque le connaît peut lire et changer ta progression. Préfère celui que
propose « Créer un code » à un mot facile à deviner. Le serveur ne reçoit jamais le code lui-même,
seulement son empreinte.

### 7.4 Mettre en place le serveur (une seule fois)

**C’est fait** : le serveur de cette appli tourne à l’adresse
`https://xingyinyi-sync.guillaume-plehar.workers.dev`, inscrite dans l’appli (constante `SYNC_URL`
de `index.html`). Les étapes ci-dessous servent à le refaire, sur un autre compte par exemple.

Le serveur est un petit programme (`outils/sync/worker.mjs`) qui tourne gratuitement chez
Cloudflare, avec une petite base de données (D1). L’offre gratuite (100 000 requêtes par jour,
500 Mo par base) dépasse de loin ce qu’il faut. Son adresse étant publique, le serveur n’accepte que
5 codes (variable `MAX_CODES` du programme, dans ses réglages, pour en permettre plus). Depuis l’ordinateur :

1. Crée un compte sur https://dash.cloudflare.com/sign-up (gratuit, sans carte bancaire).
2. **La base** : dans le menu de gauche, « Storage & Databases » › « D1 SQL Database » ›
   « Create » ; nom `xingyinyi` ; « Create ». Rien d’autre à y faire : le programme crée ses tables.
3. **Le programme** : « Compute (Workers) » › « Workers & Pages » › « Create » › « Start with Hello
   World! » ; nom `xingyinyi-sync` ; « Deploy ». Puis « Edit code » : efface tout, colle le contenu
   du fichier `outils/sync/worker.mjs` du dépôt, et « Deploy ».
4. **Relier les deux** : dans le programme `xingyinyi-sync`, onglet « Bindings » (ou « Settings » ›
   « Bindings ») › « Add binding » › « D1 database » ; « Variable name » : `DB` (en majuscules) ;
   base : `xingyinyi` ; « Add Binding », puis redéploie si Cloudflare le propose.
5. **Vérifier** : son adresse s’affiche sur la page du programme, du genre
   `https://xingyinyi-sync.TON-SOUS-DOMAINE.workers.dev`. Ouvre-la en y ajoutant `/sante` : la page
   doit afficher `"ok"`. Sinon, la liaison de l’étape 4 manque, ou son nom n’est pas `DB`.

Cette adresse (sans `/sante`) va dans la constante `SYNC_URL` de `index.html` (Claude Code s’en
charge) : il ne reste alors que le code à taper sur chaque appareil. Laissée vide, l’appli demande
l’adresse dans Réglages › Synchroniser les appareils.

Pour essayer sans Cloudflare, le même serveur tourne sur l’ordinateur (Node 22.13 ou plus) :
`node outils/sync/serveur_local.mjs`, adresse `http://localhost:8787` (la progression s’y perd à
l’arrêt, sauf avec `--base fichier.sqlite`).


## 8. Installer une nouvelle version de l’appli

Quand tu reçois une nouvelle version (un nouveau zip), copie ses fichiers par-dessus les tiens,
**sauf `decks/perso.tsv`** (et toute liste que tu as modifiée). Puis :

```sh
git add -A
git commit -m "Nouvelle version de l’appli"
git push
```

Sur l’iPhone, un bandeau « Nouvelle version de l’appli prête » apparaît : touche Recharger.
Tu peux aussi forcer la vérification : Réglages › Appli › **Vérifier** (listes et appli).

**Passage aux seaux.** La version qui introduit les seaux et la file remplace les anciennes
boîtes, les nouveaux mots par jour et les rappels HSK 1 et HSK 2. À la première ouverture après
cette mise à jour, un message te prévient : tous les mots repartent du seau 0 pour un nouveau
premier tour complet, dans l’ordre des listes. Le nombre de révisions et d’oublis de chaque mot
est gardé. C’est pareil si tu restaures une sauvegarde plus ancienne.


## 9. Faire évoluer l’appli avec Claude Code

Le fichier `CLAUDE.md` décrit l’appli pour Claude Code : il le lit tout seul au démarrage. Dans le
dossier du dépôt :

```sh
claude
```

Demande ce que tu veux changer. Avant de publier, fais lancer les tests (`py tests\test_seance.py`,
`py tests\test_seaux.py` et `py tests\test_listes.py`) puis `py outils\version_appli.py`, qui
prévient les téléphones qu’une nouvelle version existe.


## 10. En cas de souci

- **L’adresse github.io affiche une erreur 404** : attends deux minutes ; vérifie dans
  Settings › Pages que la publication est active, que le dépôt est public, et que `index.html`
  est bien à la racine du dépôt (pas dans un sous-dossier `xingyinyi/xingyinyi`).
- **`git push` refuse l’authentification** : `gh auth login`, puis `gh auth setup-git`.
- **`git push` est rejeté (« fetch first »)** : un fichier a été modifié directement sur
  github.com. Lance `git pull --rebase`, puis `git push`.
- **Le téléphone ne voit pas les nouveaux mots** : l’onglet Actions du dépôt doit montrer une
  publication terminée (coche verte). Ensuite Réglages › Chercher une mise à jour des listes ;
  le message indique un éventuel fichier introuvable. Vérifie aussi que la liste est active et
  rappelle-toi que le premier tour suit l’ordre des listes, puis celui des lignes.
- **Les révisions ne commencent pas** : le premier tour n’est pas fini (Progrès indique combien
  de mots il reste à voir). Désactive les listes que tu ne veux pas parcourir maintenant, HSK 1
  et HSK 2 par exemple (section 5).
- **Pas de voix** : installe une voix chinoise dans les réglages de l’iPhone (voir 1.5).
- **Un caractère s’affiche dans une autre police** : il n’est pas dans la police intégrée (qui
  couvre tous les caractères du HSK 2.0 et du HSK 3.0) ; l’iPhone utilise alors sa police chinoise.


Polices : LXGW WenKai et Andika, sous SIL Open Font License 1.1 (`fonts/OFL.txt`).
Listes : HSK 2.0 officiel, révision de 2012. Traductions françaises et phrases d’exemple écrites
pour cette appli.
