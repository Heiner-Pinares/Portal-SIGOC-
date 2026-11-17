import os
import tempfile

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


@pytest.fixture()
def app():
    handle, path = tempfile.mkstemp(suffix=".db")
    os.close(handle)
    app = create_app({
        "TESTING": True, "SECRET_KEY": "test-key", "DATABASE_PATH": path,
        "SIGOC_DEMO_MODE": True, "DWO_WRITE_ENABLED": False,
        "AUDIT_LOG_PATH": path + ".log",
    })
    with app.app_context():
        db = get_db()
        db.execute(
            """INSERT INTO users (username, password_hash, auth_source, display_name, role)
               VALUES ('editor', ?, 'local', 'Editora de prueba', 'editor')""",
            (generate_password_hash("secret123", method="pbkdf2:sha256:600000"),),
        )
        db.commit()
    yield app
    os.unlink(path)
    if os.path.exists(path + ".log"):
        os.unlink(path + ".log")


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_client(client):
    page = client.get("/login")
    token = page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    response = client.post("/login", data={"identity": "editor", "password": "secret123", "csrf_token": token})
    assert response.status_code == 302
    return client


@pytest.fixture()
def csrf(logged_client):
    page = logged_client.get("/")
    return page.text.split('name="csrf-token" content="', 1)[1].split('"', 1)[0]

