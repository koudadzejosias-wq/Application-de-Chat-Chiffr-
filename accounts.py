"""Comptes utilisateurs : création et vérification des identifiants (SQLite).

Les mots de passe ne sont jamais stockés en clair : seul un hachage
PBKDF2-HMAC-SHA256 avec un sel aléatoire propre à chaque compte est conservé.
"""
import hashlib
import hmac
import os
import re
import sqlite3

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "users.db"))
ITERATIONS = 200_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")
MIN_PASSWORD = 6


def _connect():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        " username TEXT PRIMARY KEY COLLATE NOCASE,"
        " salt BLOB NOT NULL,"
        " pwd_hash BLOB NOT NULL)"
    )
    return db


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)


def register(username: str, password: str) -> str | None:
    """Crée un compte. Renvoie un message d'erreur, ou None si tout va bien."""
    if not USERNAME_RE.match(username):
        return "Nom d'utilisateur invalide (3 à 20 caractères : lettres, chiffres, _ ou -)."
    if len(password) < MIN_PASSWORD:
        return f"Mot de passe trop court ({MIN_PASSWORD} caractères minimum)."
    salt = os.urandom(16)
    with _connect() as db:
        try:
            db.execute("INSERT INTO users VALUES (?, ?, ?)", (username, salt, _hash(password, salt)))
        except sqlite3.IntegrityError:
            return "Ce nom d'utilisateur existe déjà."
    return None


def login(username: str, password: str) -> str | None:
    """Vérifie les identifiants. Renvoie le nom du compte, ou None s'ils sont faux."""
    with _connect() as db:
        row = db.execute(
            "SELECT username, salt, pwd_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row and hmac.compare_digest(_hash(password, row[1]), row[2]):
        return row[0]
    return None
