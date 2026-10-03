# 形音义 : flashcards HSK à trois faces

Chaque carte est un prisme à trois faces : 形 le caractère, 音 le pinyin, 义 le sens en français.
Une fois la carte tournée, une phrase d’exemple (例) apparaît dessous, écrite avec les seuls
caractères des niveaux 1 à 3, avec son pinyin et sa traduction à la demande.

L’appli tourne sur l’iPhone, hors ligne, depuis l’écran d’accueil. Les listes de mots vivent dans
ce dossier, sur ton ordinateur : tu les modifies, tu publies avec git, et le téléphone se met à jour
tout seul. Ta progression, elle, reste sur le téléphone.

Ce que contient le dossier :

| Élément | Rôle |
|---|---|
| `index.html`, `sw.js`, `manifest.webmanifest`, icônes | l’appli |
| `decks/` | les listes de mots : c’est là que tu ajoutes et corriges des mots |
| `decks/decks.json` | la liste des listes : nom, fichier, mode, ordre de priorité |
| `outils/decks.py` | vérifier une liste, ajouter un mot, compléter le pinyin |
| `fonts/` | polices LXGW WenKai et Andika (licence libre, voir `fonts/OFL.txt`) |

Listes fournies : HSK 3 (300 mots, à apprendre), HSK 1 et HSK 2 (150 et 151 mots, en rappel,
3 mots par jour chacune), Perso (vide, pour tes mots). Les trois listes HSK sont les listes
officielles HSK 2.0 (révision de 2012), celles de l’examen de novembre.


## 1. Installation (une seule fois)

### 1.1 Préparer l’ordinateur

Il te faut un compte GitHub gratuit (https://github.com/signup), git et, pour se connecter
facilement, l’outil `gh` de GitHub.

**Sur Mac**, ouvre le Terminal (Applications › Utilitaires) :

```sh
git --version          # si git manque, macOS propose de l’installer : accepte
brew install gh        # si tu as Homebrew ; sinon télécharge gh sur https://cli.github.com
```

**Sur Windows**, installe Git for Windows (https://git-scm.com) et utilise le terminal « Git Bash »
pour toutes les commandes de ce guide. Puis : `winget install --id GitHub.cli`.

Si c’est la première fois que tu utilises git sur cet ordinateur, présente-toi :

```sh
git config --global user.name "Guillaume"
git config --global user.email "ton-adresse@exemple.fr"
```

### 1.2 Mettre le dossier sous git

Décompresse `xingyinyi-appli.zip` (double-clic) et range le dossier `xingyinyi` où tu veux le
garder, par exemple dans Documents. Puis :

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

Réponds : GitHub.com, HTTPS, « Authenticate Git with your GitHub credentials » : Yes,
« Login with a web browser ». Un code s’affiche ; colle-le dans la page qui s’ouvre. Ensuite :

```sh
gh repo create xingyinyi --public --source=. --remote=origin --push
```

Le dépôt est créé et tes fichiers sont envoyés.

> Sans `gh` : crée un dépôt vide sur https://github.com/new (nom `xingyinyi`, Public, sans
> README), puis `git remote add origin https://github.com/TON-IDENTIFIANT/xingyinyi.git` et
> `git push -u origin main`. Quand git demande un mot de passe, il faut un jeton d’accès
> (Settings › Developer settings › Personal access tokens) : c’est pour ça que `gh` est plus simple.

### 1.4 Publier avec GitHub Pages

Sur github.com, dans le dépôt `xingyinyi` : **Settings › Pages**, rubrique « Build and deployment » :
Source « Deploy from a branch », branche `main`, dossier `/ (root)`, puis **Save**.

Ou, depuis le Terminal, dans le dossier :

```sh
gh api -X POST "repos/{owner}/{repo}/pages" -f "source[branch]=main" -f "source[path]=/"
```

Une à deux minutes plus tard, l’appli est en ligne à l’adresse
`https://TON-IDENTIFIANT.github.io/xingyinyi/` (elle s’affiche aussi dans Settings › Pages).

Le dépôt doit rester public : c’est la condition de GitHub Pages gratuit. Les listes de mots sont
donc visibles par qui connaît l’adresse ; ta progression, elle, n’est jamais envoyée sur GitHub.

### 1.5 Installer sur l’iPhone

1. Ouvre l’adresse dans **Safari**.
2. Bouton Partager (le carré avec une flèche) › **Sur l’écran d’accueil** › Ajouter.
3. Lance l’appli une première fois depuis l’icône, avec du réseau : elle télécharge les listes
   et les polices. Ensuite elle marche aussi hors ligne.

Ouvre-la toujours depuis l’icône : l’appli de l’écran d’accueil garde sa propre progression,
séparée de Safari.

Pour la voix : Réglages de l’iPhone › Accessibilité › Contenu énoncé › Voix › Chinois (mandarin),
et télécharge une voix de bonne qualité.


## 2. Sur l’iPhone, au quotidien

- **Réviser** : touche la carte ou fais-la glisser pour la tourner. La face 形 montre déjà la
  phrase d’exemple en caractères (réglable). Dès que la carte a tourné, la phrase se découvre
  sous la carte (例) ; « Pinyin et traduction » affiche le reste.
  Note-toi ensuite : × raté, √ bon, 优 facile. Le haut de l’écran compte les cartes à revoir et
  les nouveaux mots du jour.
- **Mots** : chercher (caractères, pinyin sans accents ou français), filtrer par liste, ajouter un mot.
- **Progrès** : mots vus par liste, date à laquelle chaque liste sera entièrement vue,
  révisions prévues sur la semaine, et le rythme à tenir avant l’examen.
- **Réglages** : nouveaux mots par jour, listes actives, rappels par jour, date de l’examen,
  publication sur GitHub, mise à jour de l’appli (Appli › Vérifier),
  sauvegarde.

Les nouveaux mots arrivent dans l’ordre des listes : d’abord ceux ajoutés sur le téléphone, puis
Perso, puis HSK 3. Dans chaque liste, ils arrivent dans l’ordre des lignes du fichier (pour les
listes HSK : du plus fréquent au plus rare).


## 3. Ajouter ou corriger des mots depuis l’ordinateur

### Le format des listes

Chaque fichier `decks/*.tsv` contient un mot par ligne, colonnes séparées par une **tabulation** :

| Colonne | Contenu | Obligatoire |
|---|---|---|
| hanzi | le mot en caractères ; il sert d’identifiant | oui |
| pinyin | `túshūguǎn` ou `tu2shu1guan3` ; deux lectures : `zhǐ / zhī` | oui |
| francais | les sens, séparés par `;` | oui |
| note | remarque affichée sous les sens | non |
| audio | ce que la voix lit si le mot seul se lit mal (`还书` pour 还 huán) | non |
| exemple | phrase en caractères contenant le mot | non |
| exemple_pinyin | pinyin de la phrase | non |
| exemple_fr | traduction de la phrase | non |

Les lignes qui commencent par `#` sont des commentaires. Un éditeur de texte comme VS Code (ou
TextEdit, qui ouvre ces fichiers en texte brut) convient. Évite Excel : en enregistrant, il abîme
souvent les caractères chinois. Si ton éditeur remplace les tabulations par des espaces, l’appli
s’en sort quand même, `verifier` te le signale et `completer` remet des tabulations.

### Le plus simple : la commande `ajouter`

Une fois pour toutes, installe le calcul automatique du pinyin :

```sh
python3 -m pip install pypinyin
```

(Sous Windows : `py` au lieu de `python3`.) Puis, depuis le dossier `xingyinyi` :

```sh
python3 outils/decks.py ajouter 打印 "imprimer" --exemple "我要打印这张照片。" --traduction "Je dois imprimer cette photo."
```

Le mot est ajouté à la fin de `decks/perso.tsv`, avec le pinyin du mot et celui de la phrase
calculés (relis-les : les caractères à plusieurs lectures demandent un coup d’œil). Pour une autre
liste : `--liste hsk3`. Pour donner le pinyin toi-même : `--pinyin da3yin4`.

Si tu as écrit des lignes à la main sans pinyin :

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

Sur l’iPhone, attends une à deux minutes (le temps que GitHub publie), puis ouvre l’appli : elle
récupère les listes toute seule et affiche ce qui a changé (« Perso : 3 mots ajoutés »). Pour
forcer la vérification : Réglages › **Chercher une mise à jour des listes**.

### Corriger un mot

Modifie sa ligne dans le fichier et publie. Changer le pinyin, le français ou l’exemple garde la
progression du mot. Changer la colonne hanzi crée un nouveau mot (l’ancien disparaît des
révisions). Supprimer une ligne retire le mot ; si tu le remets plus tard, il retrouve sa progression.

Tu peux aussi corriger un mot sur le téléphone (Mots › le mot › Modifier) : la correction reste sur
le téléphone et prend le pas sur la liste. Reporte-la dans le fichier pour la garder partout.


## 4. Listes et mots créés sur le téléphone

### Créer, remplir, supprimer une liste

- Mots › **＋ Nouvelle liste** : donne-lui un nom (« Cours du mardi »). Elle s’ouvre aussitôt.
- Dans une liste du téléphone : **Ajouter un mot ici**, **Renommer**, **Supprimer la liste**
  (ses mots et leur progression partent avec elle).
- Le formulaire **Ajouter** a aussi un champ « Liste », avec l’option « Nouvelle liste… ».

Les listes du téléphone passent en tête des nouveaux mots. Tant qu’elles ne sont pas publiées,
elles n’existent que sur ce téléphone.

### Publier depuis le téléphone, sans l’ordinateur

L’appli peut écrire elle-même dans ton dépôt GitHub : chaque liste du téléphone devient un fichier
`decks/<nom>.tsv` déclaré dans `decks.json`, les mots de « Ajoutés ici » vont dans `perso.tsv`,
et les corrections faites sur des mots HSK sont reportées dans leur fichier. La progression est
gardée. Il lui faut un **jeton d’accès** limité à ce dépôt :

1. Sur github.com : avatar › **Settings** › **Developer settings** › **Personal access tokens** ›
   **Fine-grained tokens** › **Generate new token**.
2. Nom : `xingyinyi téléphone` ; expiration : un an ; **Repository access** : « Only select
   repositories » › `xingyinyi`.
3. **Permissions** › Repository permissions › **Contents** : « Read and write ». Rien d’autre.
4. **Generate token**, puis copie le jeton (`github_pat_…`) ; il ne s’affiche qu’une fois.
5. Dans l’appli : Réglages › **Publier depuis le téléphone** : le dépôt est déjà rempli, colle le
   jeton, **Connecter**.

Ensuite, **Publier sur GitHub** (dans Réglages, ou sous la liste de mots) envoie tout en un seul
commit. Avec le jeton, chaque liste des Réglages a aussi un bouton **Supprimer** qui la retire
du dépôt.

Le jeton reste dans l’appli, sur ce téléphone ; « Déconnecter » l’efface. S’il fuit, il ne donne
accès qu’au contenu de ce dépôt, et tu peux le révoquer sur la même page de GitHub.

**Important** : après une publication depuis le téléphone, lance `git pull` sur l’ordinateur
avant de modifier les listes, sinon `git push` sera refusé.

### Sans jeton

Mots › **Copier pour l’ordinateur** donne, pour chaque liste du téléphone, les lignes à coller et
le fichier où les mettre : `decks/perso.tsv` pour « Ajoutés ici » ; pour une autre liste, un
fichier créé avec `py outils\decks.py nouvelle-liste <id> "<nom>"` (la commande exacte est
affichée). Lance ensuite `py outils\decks.py completer` sur le fichier, puis publie avec git. À la
mise à jour suivante, ces mots passent dans la liste du dépôt du même nom en gardant leur
progression.

Un même mot peut figurer dans plusieurs listes (par exemple un mot du HSK 3 dans ta liste
« Cours du mardi ») : chaque liste a alors sa propre carte pour ce mot.


## 5. Les rappels HSK 1 et HSK 2

Les listes en mode `rappel` ne servent pas à apprendre mais à revoir des mots déjà connus.
Chaque jour, 3 mots de HSK 1 et 3 mots de HSK 2 jamais revus s’ajoutent à la séance, comptés
avec les révisions. √ renvoie le mot dans 8 jours, 优 dans 32 jours, × le fait réapprendre comme
un nouveau mot. À 3 par jour, chaque liste est passée en revue en une cinquantaine de jours.

Le nombre par jour se change dans Réglages, sur le téléphone, ou dans `decks/decks.json`
(`"parJour": 5`) : quand tu modifies le fichier, c’est lui qui l’emporte.


## 6. Ajouter une liste (par exemple le nouveau HSK 3.0)

```sh
python3 outils/decks.py nouvelle-liste hsk30-3 "HSK 3.0 niveau 3"
```

Cette commande crée `decks/hsk30-3.tsv` avec la ligne d’en-tête et inscrit la liste dans
`decks/decks.json`. Remplis le fichier, vérifie, publie. À la main, une liste se déclare ainsi
dans `decks/decks.json` :

```json
{ "id": "hsk30-3", "nom": "HSK 3.0 niveau 3", "fichier": "hsk30-3.tsv", "mode": "apprendre", "actif": true }
```

| Champ | Sens |
|---|---|
| `id` | identifiant court, à ne plus changer : la progression y est attachée |
| `nom` | nom affiché dans l’appli |
| `fichier` | fichier de la liste dans `decks/` |
| `mode` | `apprendre` (nouveaux mots) ou `rappel` (mots connus, revus peu à peu) |
| `parJour` | pour une liste de rappel, nombre de mots par jour |
| `actif` | `false` pour garder une liste sans l’utiliser |

L’ordre des listes dans `decks.json` est l’ordre de priorité des nouveaux mots. Un même mot
présent dans deux listes donne deux cartes distinctes : c’est voulu, car le sens peut différer
(还 hái dans HSK 2, 还 huán dans HSK 3).


## 7. Sauvegarder la progression

La progression n’existe que sur le téléphone. Réglages › **Exporter un fichier** l’enregistre
dans Fichiers (iCloud Drive, par exemple) ; « Restaurer » la recharge. Supprimer l’icône de
l’appli supprime aussi sa progression : exporte d’abord.


## 8. Installer une nouvelle version de l’appli

Quand tu reçois une nouvelle version (un nouveau zip), copie ses fichiers par-dessus les tiens,
**sauf `decks/perso.tsv`** (et toute liste que tu as modifiée). Puis :

```sh
git add -A
git commit -m "Nouvelle version de l’appli"
git push
```

Sur l’iPhone, un bandeau « Nouvelle version de l’appli prête » apparaît : touche Recharger.
Tu peux aussi forcer la vérification : Réglages › Appli › **Vérifier** (listes et appli).


## 9. En cas de souci

- **L’adresse github.io affiche une erreur 404** : attends deux minutes ; vérifie dans
  Settings › Pages que la publication est active, que le dépôt est public, et que `index.html`
  est bien à la racine du dépôt (pas dans un sous-dossier `xingyinyi/xingyinyi`).
- **`git push` refuse l’authentification** : `gh auth login`, puis `gh auth setup-git`.
- **`git push` est rejeté (« fetch first »)** : un fichier a été modifié directement sur
  github.com. Lance `git pull --rebase`, puis `git push`.
- **Le téléphone ne voit pas les nouveaux mots** : l’onglet Actions du dépôt doit montrer une
  publication terminée (coche verte). Ensuite Réglages › Chercher une mise à jour des listes ;
  le message indique un éventuel fichier introuvable. Vérifie aussi que la liste est active et
  rappelle-toi que les nouveaux mots arrivent dans l’ordre des lignes.
- **Pas de voix** : installe une voix chinoise dans les réglages de l’iPhone (voir 1.5).
- **Un caractère s’affiche dans une autre police** : il n’est pas dans la police intégrée (qui
  couvre tous les caractères du HSK 2.0 et du HSK 3.0) ; l’iPhone utilise alors sa police chinoise.


Polices : LXGW WenKai et Andika, sous SIL Open Font License 1.1 (`fonts/OFL.txt`).
Listes : HSK 2.0 officiel, révision de 2012. Traductions françaises et phrases d’exemple écrites
pour cette appli.
