"""Serveur de chat WebSocket : relaie les messages chiffrés à tout le salon."""
import asyncio
import json
import os
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import serve

import accounts

CLIENTS = {}  # websocket -> pseudo


async def broadcast(message: dict, exclude=None):
    data = json.dumps(message)
    for ws in list(CLIENTS):
        if ws is not exclude:
            try:
                await ws.send(data)
            except Exception:
                pass


async def authenticate(ws):
    """Gère la création de compte et la connexion. Renvoie le pseudo une fois connecté.

    Messages acceptés tant que l'utilisateur n'est pas connecté :
      {"type": "register", "username": "...", "password": "..."}
      {"type": "login",    "username": "...", "password": "..."}
    """
    while True:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=300))
        username = str(msg.get("username", "")).strip()
        password = str(msg.get("password", ""))
        if msg.get("type") == "register":
            error = await asyncio.to_thread(accounts.register, username, password)
            if error:
                await ws.send(json.dumps({"type": "error", "text": error}))
            else:
                await ws.send(json.dumps({"type": "registered", "text": "Compte créé ! Vous pouvez vous connecter."}))
        elif msg.get("type") == "login":
            pseudo = await asyncio.to_thread(accounts.login, username, password)
            if not pseudo:
                await ws.send(json.dumps({"type": "error", "text": "Nom d'utilisateur ou mot de passe incorrect."}))
            elif pseudo in CLIENTS.values():
                await ws.send(json.dumps({"type": "error", "text": "Ce compte est déjà connecté au salon."}))
            else:
                return pseudo
        else:
            await ws.send(json.dumps({"type": "error", "text": "Connectez-vous d'abord."}))


async def handler(ws):
    pseudo = None
    try:
        pseudo = await authenticate(ws)
        CLIENTS[ws] = pseudo
        await ws.send(json.dumps({"type": "ok", "pseudo": pseudo, "users": sorted(CLIENTS.values())}))
        await broadcast({"type": "system", "text": f"{pseudo} a rejoint le salon"}, exclude=ws)

        async for raw in ws:
            msg = json.loads(raw)
            if msg.get("type") == "message" and isinstance(msg.get("data"), str):
                # Le serveur ne voit que du texte chiffré
                await broadcast({"type": "message", "data": msg["data"]}, exclude=ws)
            elif msg.get("type") == "quit":
                break
    except Exception:
        pass
    finally:
        if ws in CLIENTS:
            del CLIENTS[ws]
            await broadcast({"type": "system", "text": f"{pseudo} a quitté le salon"})


INDEX_HTML = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


async def http_handler(connection, request):
    """Répond aux requêtes HTTP : client web sur /, état du serveur sur /health."""
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None  # laisse passer la connexion WebSocket
    if request.path.startswith("/health"):
        return connection.respond(
            HTTPStatus.OK,
            f"Serveur de chat chiffré en ligne. {len(CLIENTS)} utilisateur(s) connecté(s).\n",
        )
    response = connection.respond(HTTPStatus.OK, INDEX_HTML)
    del response.headers["Content-Type"]
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


async def main():
    port = int(os.environ.get("PORT", 8765))
    async with serve(handler, "0.0.0.0", port, process_request=http_handler):
        print(f"Serveur démarré sur le port {port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
