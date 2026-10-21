# Application de Chat Chiffré (Client/Serveur)

## Description

Chat en temps réel dans un salon unique, avec chiffrement AES des messages.

- **Comptes utilisateurs** : chaque personne crée son compte (nom d'utilisateur + mot de passe), puis se connecte
- Pseudo choisi au démarrage : c'est le nom d'utilisateur du compte (unique)
- Messages envoyés à tout le salon et affichés en temps réel (WebSocket)
- Messages chiffrés en AES-256-GCM **avant** l'envoi
- Commande `/quit` pour quitter proprement
- Notifications « X a rejoint / quitté le salon »

Deux clients au choix, compatibles entre eux (même salon, même chiffrement) :
- **Client web** : ouvrir le lien public dans un navigateur.
- **Client terminal** : `python client.py`.

Fichiers : `server.py` (serveur WebSocket + page web), `accounts.py` (comptes), `index.html` (client web), `client.py` (client terminal), `crypto_utils.py` (AES).

## Installation

Python 3.10+ requis.

```bash
pip install -r requirements.txt
```

## Utilisation

Serveur (local) :

```bash
python server.py
```

Client, vers le serveur en ligne (par défaut) :

```bash
python client.py
```

Client, vers un serveur local :

```bash
python client.py --url ws://localhost:8765
```

Au lancement, le client propose :

```
1) Se connecter
2) Créer un compte
```

Créez d'abord votre compte (2), puis connectez-vous (1) : vous rejoignez alors le salon avec votre nom d'utilisateur comme pseudo. Le mot de passe est masqué pendant la saisie. Sur le client web, utilisez les onglets **Créer un compte** puis **Se connecter**.

Règles : nom d'utilisateur de 3 à 20 caractères (lettres, chiffres, `_` ou `-`), mot de passe d'au moins 6 caractères. Un même compte ne peut pas être connecté deux fois en même temps.

Tous les clients doivent utiliser la même phrase secrète (option `--secret "ma phrase"`, valeur par défaut incluse) pour pouvoir se lire.

## Lien public de l'application

**https://application-de-chat-chiffre.onrender.com** : ouvrir ce lien donne directement l'interface de chat (serveur déployé gratuitement sur Render, via `render.yaml`).

État du serveur : https://application-de-chat-chiffre.onrender.com/health

Github : https://github.com/koudadzejosias-wq/Application-de-Chat-Chiffr-

## Explication du chiffrement

- **Algorithme** : AES-256 en mode **GCM** (chiffrement + authentification), via la bibliothèque `cryptography` (client Python) et l'API Web Crypto du navigateur (client web).
- **Clé** : dérivée de la phrase secrète du salon avec PBKDF2-HMAC-SHA256 (200 000 itérations). Elle n'est jamais envoyée sur le réseau.
- **Nonce** : 12 octets aléatoires, différents pour chaque message, placés devant le texte chiffré puis encodés en base64.
- **Contenu chiffré** : le pseudo et le texte du message. Le serveur ne reçoit et ne relaie que du texte chiffré illisible pour lui (chiffrement de bout en bout entre clients).
- **Intégrité** : GCM détecte toute modification ; un message altéré ou chiffré avec une autre clé est rejeté.
- **Mots de passe** : jamais stockés en clair. Le serveur conserve seulement un hachage PBKDF2-HMAC-SHA256 (200 000 itérations) avec un sel aléatoire propre à chaque compte, dans une base SQLite (`users.db`). La vérification se fait en temps constant (`hmac.compare_digest`).
- Les notifications d'arrivée/départ sont générées par le serveur et ne sont pas chiffrées.
- La connexion en ligne utilise `wss://` (TLS fourni par l'hébergeur), en plus du chiffrement AES.

## Déploiement (Render, gratuit)

1. Créer un compte sur render.com, puis **New + → Blueprint** et choisir ce dépôt (`render.yaml` configure tout).
2. Pour que le serveur reste éveillé 24h/24 (l'offre gratuite s'endort après 15 min d'inactivité), créer un moniteur gratuit sur uptimerobot.com qui interroge `https://application-de-chat-chiffre.onrender.com/health` toutes les 5 minutes.
