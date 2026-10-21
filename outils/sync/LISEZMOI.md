# Serveur de synchronisation

La mise en place, pas à pas, est dans le guide principal : `LISEZMOI.md`, section 7.4. Ce fichier
décrit le fonctionnement.

| Fichier | Rôle |
|---|---|
| `worker.mjs` | Le serveur : un Cloudflare Worker relié à une base D1 sous le nom `DB`. À coller tel quel dans l’éditeur de Cloudflare. |
| `serveur_local.mjs` | Le même serveur sur l’ordinateur, la base D1 imitée par `node:sqlite` (Node 22.13 ou plus) : `node outils/sync/serveur_local.mjs [--port 8787] [--base fichier.sqlite]`. Sert aux tests. |

## Ce que garde le serveur

Une ligne par code commun : `docs (k, v, data, at)`. `k` est l’empreinte SHA-256 de
`"xingyinyi:" + code` (le code ne quitte jamais l’appareil), `v` un numéro de version, `data` le
document JSON partagé (progression, historique, mots, listes, corrections, réglages). Une copie de la
version remplacée va dans `copies (k, at, v, data)` si la dernière a plus de 20 heures ; 30 copies au
plus par code. Les tables se créent au premier appel.

## Adresses

| Requête | Réponse |
|---|---|
| `GET /sante` | `"ok"` si la base répond |
| `GET /p/<clé>?have=<v>` | `{v, data}`, ou `{v}` seul si l’appareil a déjà la version `v`, ou `{v: 0, data: null}` |
| `PUT /p/<clé>` avec `{v, data}` | `{v: v + 1}` si le serveur en est toujours à `v` (`v = 0` : premier envoi), sinon **409** et `{v, data}` actuels |
| `GET /p/<clé>/copies` | `{copies: [{at, v, size}]}`, de la plus récente à la plus ancienne |
| `GET /p/<clé>/copies/<at>` | `{at, v, data}` |

Le serveur ne fusionne rien : le 409 évite seulement qu’un appareil écrase ce qu’un autre vient
d’envoyer. L’appli (`index.html`, section « sync between devices ») garde le dernier document reçu
ou envoyé (sa « base »), fusionne mot par mot ce qui a changé de chaque côté depuis, et renvoie le
résultat. Documents de 1,9 Mo au plus (D1 : 2 Mo par ligne).

## Tests

```powershell
node tests\test_serveur_sync.mjs      # le serveur seul, sans réseau
py tests\test_sync.py                 # deux appareils (téléphone et ordinateur) et le serveur local
```
