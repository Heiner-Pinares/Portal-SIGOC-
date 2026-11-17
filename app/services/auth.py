import re

from flask import current_app
from werkzeug.security import check_password_hash

from app.db import get_db


CORPORATE_CODE = re.compile(r"^[CE][0-9]{5}$", re.I)
CORPORATE_MAIL_CODE = re.compile(r"^([CE][0-9]{5})@([A-Z0-9.-]+)$", re.I)


class AuthenticationUnavailable(RuntimeError):
    pass


def classify_identity(identity):
    normalized = identity.strip().upper()
    if CORPORATE_CODE.fullmatch(normalized):
        return "corporate_code", normalized
    match = CORPORATE_MAIL_CODE.fullmatch(normalized)
    if match and match.group(2).lower() in current_app.config["CLARO_EMAIL_DOMAINS"]:
        return "corporate_code", match.group(1).upper()
    if "@" in identity and identity.rsplit("@", 1)[1].lower() in current_app.config["CLARO_EMAIL_DOMAINS"]:
        return "corporate_email", identity.lower()
    return "local", identity.strip()


def authenticate(identity, password):
    kind, normalized = classify_identity(identity)
    if kind == "corporate_email":
        db = get_db()
        matches = db.execute(
            "SELECT username FROM users WHERE auth_source = 'ldap' AND lower(email) = lower(?)",
            (normalized,),
        ).fetchall()
        if len(matches) != 1:
            return None
        normalized = matches[0]["username"].upper()
        kind = "corporate_code"
    if kind == "corporate_code":
        return _authenticate_ldap(normalized, password)
    return _authenticate_local(normalized, password)


def _authenticate_local(username, password):
    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE lower(username) = lower(?) AND auth_source = 'local'",
        (username,),
    ).fetchone()
    if not row or not row["is_active"] or not row["password_hash"]:
        return None
    return dict(row) if check_password_hash(row["password_hash"], password) else None


def _authenticate_ldap(code, password):
    try:
        from Crypto.Hash import MD4  # noqa: F401
        from ldap3 import ALL, Connection, NTLM, Server, Tls
        from ldap3.utils.conv import escape_filter_chars
    except ImportError as exc:
        raise AuthenticationUnavailable("Dependencia LDAP/NTLM no disponible") from exc
    cfg = current_app.config
    mode = cfg["LDAP_MODE"].lower()
    use_ssl = mode == "ldaps"
    port = 636 if use_ssl else 389
    tls = Tls(ca_certs_file=cfg["LDAP_CA_CERT"] or None, validate=2) if mode in {"ldaps", "starttls"} else None
    server = Server(cfg["LDAP_HOST"], port=port, use_ssl=use_ssl, tls=tls, get_info=ALL,
                    connect_timeout=cfg["LDAP_CONNECT_TIMEOUT"])
    connection = None
    try:
        connection = Connection(
            server, user=f"{cfg['LDAP_NETBIOS']}\\{code}", password=password,
            authentication=NTLM, receive_timeout=cfg["LDAP_RESPONSE_TIMEOUT"], auto_bind=False,
        )
        connection.open()
        if mode == "starttls" and not connection.start_tls():
            raise AuthenticationUnavailable("No se pudo establecer StartTLS")
        if not connection.bind():
            return None
        safe_code = escape_filter_chars(code)
        connection.search(
            cfg["LDAP_BASE_DN"], f"(sAMAccountName={safe_code})",
            attributes=["sAMAccountName", "givenName", "sn", "mail", "displayName", "userAccountControl"],
            size_limit=2,
        )
        if len(connection.entries) != 1:
            return None
        entry = connection.entries[0]
        if str(entry.sAMAccountName).upper() != code or int(entry.userAccountControl.value or 0) & 2:
            return None
        return _sync_ldap_user(code, {
            "given_name": str(entry.givenName or ""), "surname": str(entry.sn or ""),
            "email": str(entry.mail or ""), "display_name": str(entry.displayName or code),
        })
    except AuthenticationUnavailable:
        raise
    except Exception as exc:
        current_app.logger.warning("Fallo LDAP controlado: %s", type(exc).__name__)
        raise AuthenticationUnavailable("Active Directory no disponible") from exc
    finally:
        if connection:
            connection.unbind()


def _sync_ldap_user(code, profile):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (code,)).fetchone()
    if row:
        db.execute(
            """UPDATE users SET password_hash = NULL, auth_source = 'ldap', display_name = ?,
               given_name = ?, surname = ?, email = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (profile["display_name"], profile["given_name"], profile["surname"], profile["email"], row["id"]),
        )
    else:
        db.execute(
            """INSERT INTO users
               (username, password_hash, auth_source, display_name, given_name, surname, email, role)
               VALUES (?, NULL, 'ldap', ?, ?, ?, ?, 'consulta')""",
            (code, profile["display_name"], profile["given_name"], profile["surname"], profile["email"]),
        )
    db.commit()
    return dict(db.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (code,)).fetchone())

