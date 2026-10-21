"""Client de chat chiffré (terminal)."""
import argparse
import asyncio
import getpass
import json
import sys

from websockets.asyncio.client import connect

from crypto_utils import decrypt, derive_key, encrypt

DEFAULT_URL = "wss://application-de-chat-chiffre.onrender.com"
DEFAULT_SECRET = "chat-chiffre"


async def receive(ws, key):
    async for raw in ws:
        msg = json.loads(raw)
        if msg["type"] == "system":
            print(f"\r*** {msg['text']} ***")
        elif msg["type"] == "message":
            try:
                d = decrypt(key, msg["data"])
                print(f"\r[{d['pseudo']}] {d['text']}")
            except Exception:
                print("\r[message illisible : mauvaise clé de chiffrement]")


async def send(ws, key, pseudo):
    while True:
        try:
            line = await asyncio.to_thread(input, "")
        except (EOFError, KeyboardInterrupt):
            line = "/quit"
        line = line.strip()
        if not line:
            continue
        if line == "/quit":
            await ws.send(json.dumps({"type": "quit"}))
            return
        await ws.send(json.dumps({"type": "message", "data": encrypt(key, pseudo, line)}))


def ask_password(prompt):
    # getpass masque la saisie ; repli sur input() si l'entrée n'est pas un terminal
    return getpass.getpass(prompt) if sys.stdin.isatty() else input(prompt)


async def authenticate(ws):
    """Menu de connexion / création de compte. Renvoie la réponse "ok" du serveur."""
    while True:
        choice = input("\n1) Se connecter\n2) Créer un compte\nVotre choix : ").strip()
        if choice not in ("1", "2"):
            continue
        username = input("Nom d'utilisateur : ").strip()
        password = ask_password("Mot de passe : ")
        if choice == "2":
            if ask_password("Confirmer le mot de passe : ") != password:
                print("Les deux mots de passe ne correspondent pas.")
                continue
            await ws.send(json.dumps({"type": "register", "username": username, "password": password}))
        else:
            await ws.send(json.dumps({"type": "login", "username": username, "password": password}))
        reply = json.loads(await ws.recv())
        if reply["type"] == "ok":
            return reply
        print(reply["text"])


async def run(url, secret):
    key = derive_key(secret)
    async with connect(url) as ws:
        reply = await authenticate(ws)
        pseudo = reply["pseudo"]
        print(f"Connecté en tant que {pseudo} ! Utilisateurs : {', '.join(reply['users'])}")
        print("Tapez un message et Entrée. /quit pour quitter.")
        recv_task = asyncio.create_task(receive(ws, key))
        await send(ws, key, pseudo)
        recv_task.cancel()
    print("Déconnecté. À bientôt !")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client de chat chiffré")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL du serveur (ws:// ou wss://)")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Phrase secrète du salon (clé AES)")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.url, args.secret))
    except (ConnectionError, OSError) as e:
        sys.exit(f"Connexion impossible : {e}")
