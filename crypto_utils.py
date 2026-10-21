"""Chiffrement AES-256-GCM des messages (partagé par les clients).

Le serveur ne connaît jamais la clé : il ne relaie que du texte chiffré.
"""
import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SALT = b"chat-chiffre-tp-v1"
ITERATIONS = 200_000


def derive_key(passphrase: str) -> bytes:
    """Dérive une clé AES-256 (32 octets) depuis la phrase secrète du salon."""
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), SALT, ITERATIONS, dklen=32)


def encrypt(key: bytes, pseudo: str, text: str) -> str:
    """Chiffre {pseudo, text} et renvoie nonce+ciphertext encodé en base64."""
    nonce = os.urandom(12)  # unique pour chaque message
    payload = json.dumps({"pseudo": pseudo, "text": text}).encode()
    ciphertext = AESGCM(key).encrypt(nonce, payload, None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt(key: bytes, token: str) -> dict:
    """Déchiffre un message ; lève une exception si la clé est mauvaise ou le message altéré."""
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:12], raw[12:]
    return json.loads(AESGCM(key).decrypt(nonce, ciphertext, None))
