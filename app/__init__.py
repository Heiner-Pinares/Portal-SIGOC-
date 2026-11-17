import os
import click

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

from app.config import Config
from app.db import close_db, init_db
from app.security import csrf_token, load_user, validate_csrf
from app.services.audit import configure_audit_logger


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if app.config["APP_ENV"] == "production" and app.config["SECRET_KEY"] == "development-only-change-me":
        raise RuntimeError("APP_SECRET_KEY es obligatoria en producción")
    os.makedirs(app.instance_path, exist_ok=True)

    from app.web import bp
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    app.before_request(load_user)
    app.before_request(validate_csrf)
    app.jinja_env.globals["csrf_token"] = csrf_token
    configure_audit_logger(app)

    @app.cli.command("create-local-user")
    @click.option("--username", prompt=True)
    @click.option("--display-name", prompt=True)
    @click.option("--role", type=click.Choice(["consulta", "editor", "administrador"]), default="consulta")
    @click.password_option()
    def create_local_user(username, display_name, role, password):
        """Crea o actualiza una cuenta local no corporativa."""
        from werkzeug.security import generate_password_hash
        from app.db import get_db
        from app.services.auth import CORPORATE_CODE
        normalized = username.strip()
        if CORPORATE_CODE.fullmatch(normalized) or normalized.lower().endswith("@claro.com.pe"):
            raise click.ClickException("Las identidades corporativas no pueden tener contraseña local")
        db = get_db()
        db.execute(
            """INSERT INTO users (username, password_hash, auth_source, display_name, role)
               VALUES (?, ?, 'local', ?, ?)
               ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,
                   display_name=excluded.display_name, role=excluded.role, auth_source='local', is_active=1""",
            (normalized, generate_password_hash(password, method="pbkdf2:sha256:600000"), display_name, role),
        )
        db.commit()
        click.echo(f"Usuario local {normalized} guardado.")

    @app.cli.command("diagnose")
    def diagnose():
        """Muestra dependencias y conectividad sin realizar escrituras."""
        import importlib.util
        checks = {name: bool(importlib.util.find_spec(name)) for name in ("oracledb", "ldap3", "Crypto")}
        click.echo(f"Modo: {'simulación' if app.config['SIGOC_DEMO_MODE'] else 'corporativo'}")
        for name, ok in checks.items():
            click.echo(f"{name}: {'OK' if ok else 'NO DISPONIBLE'}")
        if app.config["LDAP_MODE"] == "plano":
            click.echo("ADVERTENCIA: LDAP plano configurado; solicitar StartTLS o LDAPS a TI.")
        pools = app.extensions.get("oracle_pools")
        if pools:
            click.echo(f"PVUDB: {pools.health('pvudb')}")
            click.echo(f"DWO: {pools.health('dwo')}")
            try:
                columns = app.extensions["dwo"].inspect_schema()
                click.echo(f"Columnas DWO visibles: {len(columns)}")
            except Exception as exc:
                click.echo(f"Metadatos DWO: ERROR {type(exc).__name__}: {exc}")

    with app.app_context():
        init_db()
        _configure_repositories(app)

    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith("/api/"):
            return jsonify(error=getattr(error, "description", "Solicitud inválida")), 400
        return error

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="Recurso no encontrado"), 404
        return "Página no encontrada", 404

    return app


def _configure_repositories(app):
    from app.repositories.demo import DemoPVUDBRepository
    from app.repositories.dwo import DWORepository, DemoDWORepository
    from app.repositories.oracle import OraclePools
    from app.repositories.pvudb import PVUDBRepository

    if app.config["SIGOC_DEMO_MODE"]:
        app.extensions["pvudb"] = DemoPVUDBRepository()
        app.extensions["dwo"] = DemoDWORepository()
        app.extensions["oracle_pools"] = None
    else:
        pools = OraclePools(app.config)
        app.extensions["oracle_pools"] = pools
        app.extensions["pvudb"] = PVUDBRepository(pools, app.config["PVUDB_CAMPAIGN_SQL_FILE"])
        app.extensions["dwo"] = DWORepository(pools, app.config)

