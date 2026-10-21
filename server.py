"""Serveur de chat WebSocket : relaie les messages chiffrés à tout le salon."""
import asyncio
import json
import os
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import serve

CLIENTS = {}  # websocket -> pseudo


async def broadcast(message: dict, exclude=None):
    data = json.dumps(message)
    for ws in list(CLIENTS):
        if ws is not exclude:
            try:
                await ws.send(data)
            except Exception:
                pass


async def handler(ws):
    pseudo = None
    try:
        # Premier message obligatoire : {"type": "join", "pseudo": "..."}
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
        pseudo = str(hello.get("pseudo", "")).strip()[:20]
        if hello.get("type") != "join" or not pseudo:
            await ws.send(json.dumps({"type": "error", "text": "Pseudo invalide."}))
            return
        if pseudo in CLIENTS.values():
            await ws.send(json.dumps({"type": "error", "text": "Pseudo déjà utilisé."}))
            pseudo = None
            return

        CLIENTS[ws] = pseudo
        await ws.send(json.dumps({"type": "ok", "users": sorted(CLIENTS.values())}))
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
