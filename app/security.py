import secrets
import time
from functools import wraps

from flask import abort, g, jsonify, request, session

from app.db import get_db


_attempts = {}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def validate_csrf():
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not supplied or not secrets.compare_digest(str(supplied), str(session.get("csrf_token", ""))):
            abort(400, description="Token CSRF inválido")


def load_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row and row["is_active"]:
            g.user = dict(row)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            if request.path.startswith("/api/"):
                return jsonify(error="Autenticación requerida"), 401
            from flask import redirect, url_for
            return redirect(url_for("web.login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user["role"] not in roles:
                return jsonify(error="No tienes permisos para esta operación"), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator


def login_rate_limited(key):
    now = time.time()
    values = [stamp for stamp in _attempts.get(key, []) if now - stamp < 300]
    _attempts[key] = values
    return len(values) >= 5


def record_login_failure(key):
    _attempts.setdefault(key, []).append(time.time())


def clear_login_failures(key):
    _attempts.pop(key, None)

