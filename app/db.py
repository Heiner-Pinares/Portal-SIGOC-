import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT,
    auth_source TEXT NOT NULL CHECK (auth_source IN ('local', 'ldap')),
    display_name TEXT NOT NULL,
    given_name TEXT,
    surname TEXT,
    email TEXT,
    role TEXT NOT NULL DEFAULT 'consulta' CHECK (role IN ('consulta', 'editor', 'administrador')),
    is_active INTEGER NOT NULL DEFAULT 1,
    area TEXT,
    gerencia TEXT,
    direccion TEXT,
    manager TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    correlation_id TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    operation TEXT NOT NULL,
    campaign TEXT,
    record_key TEXT,
    result TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(correlation_id);
"""


def get_db():
    if "db" not in g:
        path = Path(current_app.config["DATABASE_PATH"])
        path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    if current_app.config["SIGOC_DEMO_MODE"]:
        username = current_app.config["DEMO_USER"]
        password = current_app.config["DEMO_PASSWORD"]
        if password:
            db.execute(
                """INSERT OR IGNORE INTO users
                   (username, password_hash, auth_source, display_name, role)
                   VALUES (?, ?, 'local', 'Usuario de demostración', 'editor')""",
                (username, generate_password_hash(password, method="pbkdf2:sha256:600000")),
            )
    db.commit()

