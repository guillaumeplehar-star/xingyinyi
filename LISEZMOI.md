# 形音义 : flashcards HSK à trois faces

Chaque carte est un prisme à trois faces : 形 le caractère, 音 le pinyin, 义 le sens en français.
Une fois la carte tournée, une phrase d’exemple (例) apparaît dessous, écrite avec les seuls
caractères des niveaux 1 à 3, avec sa traduction à la demande ; son pinyin est sur la face 音,
où tu peux aussi l’écouter.

L’appli tourne sur l’iPhone, hors ligne, depuis l’écran d’accueil. Les listes de mots vivent dans
ce dossier, sur ton ordinateur : tu les modifies, tu publies avec git, et le téléphone se met à jour
tout seul. Ta progression, elle, reste sur le téléphone.

Ce que contient le dossier :

| Élément | Rôle |
|---|---|
| `index.html`, `sw.js`, `manifest.webmanifest`, icônes | l’appli |
| `decks/` | les listes de mots : c’est là que tu ajoutes et corriges des mots |
| `decks/decks.json` | la liste des listes : nom, fichier, active ou non ; leur ordre est celui du premier tour |
| `outils/decks.py` | vérifier une liste, ajouter un mot, compléter le pinyin |
| `fonts/` | polices LXGW WenKai et Andika (licence libre, voir `fonts/OFL.txt`) |
| `CLAUDE.md`, `tests/`, `outils/version_appli.py` | pour faire évoluer l’appli avec Claude Code (section 9) |

Listes fournies : HSK 3 (300 mots), HSK 2 et HSK 1 (151 et 150 mots), Perso (vide, pour tes
mots). Les trois listes HSK sont les listes officielles HSK 2.0 (révision de 2012), celles de
l’examen de novembre. Toutes sont actives au départ : pour te concentrer sur le HSK 3, désactive
HSK 1 et HSK 2 (voir section 5).


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
  **Phrase** lisent à voix haute le mot ou la phrase. Dès que la carte a tourné, la phrase en
  caractères se découvre sous la carte (例) ; « Traduction » affiche sa traduction. Pendant la révision, le pinyin de
  la phrase n’est que sur la face 音 ; la fiche du mot (onglet Mots) montre tout.
  Note-toi ensuite : × **Raté** ou √ **Réussi** (au clavier : 1 et 2). Sous chaque bouton, l’appli
  écrit où ira le mot, par exemple « seau 0, fin de file » sous × et « seau 2, 3 jours » sous √.
  Sous la carte, une étiquette indique « Nouveau mot » ou le seau du mot.
  Le haut de l’écran compte les mots **à voir** (pas encore passés au premier tour) et les mots
  **à revoir** (ratés, ou dont le délai est écoulé). Comment avance la file : section 5.
- **＋** (en haut à droite, depuis n’importe quel écran) : créer une nouvelle fiche tout de suite.
- **Mots** : chercher (caractères, pinyin sans accents ou français), filtrer par liste ou par
  avancement (À voir, En cours, Acquis : les deux derniers seaux), ajouter un mot. La fiche d’un
  mot indique son seau et sa prochaine révision.
  Si la recherche ne trouve rien, **Créer la fiche « … »** ouvre le formulaire déjà rempli avec ce
  que tu as tapé.
- **Progrès** : mots passés, en tout et par liste, ce qu’il reste à voir au premier tour et quand
  il sera fini à ton rythme, le rythme à tenir avant l’examen, le nombre de mots dans chaque seau
  et les révisions prévues sur la semaine. C’est aussi là que tu lances une **évaluation** ou un
  **entraînement libre** (section 5).
- **Réglages** : listes actives, seaux et délais, nombre de mots par évaluation, date de l’examen,
  publication sur GitHub, affichage des cartes et voix, mise à jour de l’appli (Appli › Vérifier),
  sauvegarde.

Le premier tour suit l’ordre des listes actives : d’abord celles créées sur le téléphone (dont
« Ajoutés ici »), puis Perso, HSK 3, HSK 2 et HSK 1, dans l’ordre de `decks/decks.json`. Dans
chaque liste, les mots arrivent dans l’ordre des lignes du fichier (pour les listes HSK : du plus
fréquent au plus rare).


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
- Dans une liste du téléphone : **Ajouter un mot ici**, **Renommer**, **Supprimer la liste**
  (ses mots et leur progression partent avec elle).
- Le formulaire **Ajouter** (ou le bouton **＋** en haut de l’écran) a aussi un champ « Liste »,
  avec l’option « Nouvelle liste… ».

Les listes du téléphone passent en tête du premier tour. Tant qu’elles ne sont pas publiées,
elles n’existent que sur ce téléphone.

### Publier depuis le téléphone, sans l’ordinateur

L’appli peut écrire elle-même dans ton dépôt GitHub : chaque liste du téléphone devient un fichier
`decks/<nom>.tsv` déclaré dans `decks.json`, les mots de « Ajoutés ici » vont dans `perso.tsv`,
et les corrections faites sur des mots HSK sont reportées dans leur fichier. La progression est
gardée. Il lui faut un **jeton d’accès** limité à ce dépôt :

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
progression.

Un même mot peut figurer dans plusieurs listes (par exemple un mot du HSK 3 dans ta liste
« Cours du mardi ») : chaque liste a alors sa propre carte pour ce mot.


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

**Pour te concentrer sur le HSK 3** : dans Réglages › Listes, désactive HSK 1 et HSK 2. Sinon le
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
| `actif` | `false` pour garder une liste sans l’utiliser ; quand tu changes cette valeur, elle l’emporte sur l’interrupteur du téléphone |

L’ordre des listes dans `decks.json` est l’ordre du premier tour (après les listes du téléphone).
Les champs `mode` et `parJour` des anciennes versions (listes de rappel, mots par jour) ne servent
plus : un ancien fichier peut les garder, l’appli les ignore et `verifier` te signale que tu peux
les enlever. Un même mot présent dans deux listes donne deux cartes distinctes : c’est voulu, car
le sens peut différer (还 hái dans HSK 2, 还 huán dans HSK 3).


## 7. Sauvegarder la progression

La progression n’existe que sur le téléphone. Réglages › **Exporter un fichier** l’enregistre
dans Fichiers (iCloud Drive, par exemple) ; « Restaurer » la recharge. Supprimer l’icône de
l’appli supprime aussi sa progression : exporte d’abord. Une sauvegarde faite avant le passage
aux seaux se restaure aussi, mais tous ses mots repartent du seau 0 (voir section 8).


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
