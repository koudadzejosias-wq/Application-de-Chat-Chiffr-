"""Client de chat chiffré (terminal)."""
import argparse
import asyncio
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


async def run(url, secret):
    pseudo = input("Choisissez votre pseudo : ").strip()
    key = derive_key(secret)
    async with connect(url) as ws:
        await ws.send(json.dumps({"type": "join", "pseudo": pseudo}))
        reply = json.loads(await ws.recv())
        if reply["type"] == "error":
            print("Erreur :", reply["text"])
            return
        print(f"Connecté ! Utilisateurs : {', '.join(reply['users'])}")
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
