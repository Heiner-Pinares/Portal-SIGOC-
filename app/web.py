from datetime import datetime, timezone
import uuid

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, request, session, url_for

from app.security import (
    clear_login_failures, login_rate_limited, login_required, record_login_failure, roles_required,
)
from app.services.audit import audit
from app.services.auth import AuthenticationUnavailable, authenticate
from app.services.offers import ValidationError, calculate_preview


bp = Blueprint("web", __name__)


def _repo(name):
    return current_app.extensions[name]


def _correlation_id():
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


@bp.get("/login")
def login():
    if g.user:
        return redirect(url_for("web.index"))
    return render_template("login.html")


@bp.post("/login")
def login_post():
    identity = request.form.get("identity", "").strip()
    password = request.form.get("password", "")
    key = f"{request.remote_addr}:{identity.lower()}"
    if login_rate_limited(key):
        return render_template("login.html", error="Demasiados intentos. Espera unos minutos."), 429
    try:
        user = authenticate(identity, password)
    except AuthenticationUnavailable:
        audit("login", "provider_unavailable", _correlation_id(), details={"identity_type": "corporate"})
        return render_template("login.html", error="No pudimos validar tu contraseña de dominio en este momento. Intenta nuevamente en unos minutos."), 503
    if not user:
        record_login_failure(key)
        audit("login", "denied", _correlation_id(), details={"identity": identity[:80]})
        return render_template("login.html", error="Usuario o contraseña incorrectos."), 401
    clear_login_failures(key)
    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    audit("login", "success", _correlation_id(), user=user)
    return redirect(url_for("web.index"))


@bp.post("/logout")
@login_required
def logout():
    audit("logout", "success", _correlation_id(), user=g.user)
    session.clear()
    return redirect(url_for("web.login"))


@bp.get("/")
@login_required
def index():
    return render_template("app.html", active="register")


@bp.get("/vigencia")
@login_required
def validity():
    return render_template("app.html", active="validity")


@bp.get("/estado")
@login_required
def state():
    return render_template("app.html", active="state")


@bp.get("/historico")
@login_required
def history():
    return render_template("app.html", active="history")


@bp.get("/api/status")
@login_required
def status():
    pools = current_app.extensions.get("oracle_pools")
    connections = {"pvudb": {"ok": False, "message": "Modo simulación"}, "dwo": {"ok": False, "message": "Modo simulación"}}
    if pools:
        connections = {"pvudb": pools.health("pvudb"), "dwo": pools.health("dwo")}
    return jsonify(
        mode="demo" if current_app.config["SIGOC_DEMO_MODE"] else "oracle",
        write_enabled=current_app.config["DWO_WRITE_ENABLED"],
        write_gate_open=current_app.config.get("DWO_WRITE_ENABLED", False)
            and current_app.config.get("DWO_MAPPING_VERIFIED", False)
            and current_app.config.get("DWO_BUSINESS_RULES_VERIFIED", False)
            and current_app.config.get("DWO_KEY_VERIFIED", False),
        connections=connections,
    )


@bp.get("/api/campanas/<codigo>")
@login_required
def campaign(codigo):
    if not codigo.isdigit() or len(codigo) > 12:
        return jsonify(error="Código de campaña inválido"), 400
    try:
        records = _repo("pvudb").find_campaign(codigo)
    except Exception as exc:
        current_app.logger.exception("No se pudo consultar PVUDB")
        return jsonify(error="No se pudo consultar la campaña", detail=str(exc) if current_app.debug else None), 503
    if not records:
        return jsonify(error="Campaña no encontrada"), 404
    audit("campaign.search", "success", _correlation_id(), user=g.user, campaign=codigo,
          details={"records": len(records), "source": "demo" if current_app.config["SIGOC_DEMO_MODE"] else "pvudb"})
    return jsonify(campaign={"code": codigo, "name": records[0].campaign_name}, records=[item.to_dict() for item in records])


def _offer_payload():
    payload = request.get_json(silent=True) or {}
    campaign_code = str(payload.get("campaign", ""))
    if not campaign_code.isdigit():
        raise ValidationError("Código de campaña inválido")
    records = _repo("pvudb").find_campaign(campaign_code)
    existing = _repo("dwo").existing_by_keys(payload.get("selected_keys", []))
    preview = calculate_preview(
        records, payload.get("selected_keys", []), payload.get("discount_type"),
        payload.get("discount_value"), payload.get("period"), existing,
    )
    return campaign_code, preview


@bp.post("/api/ofertas/previsualizar")
@roles_required("editor", "administrador")
def preview_offer():
    try:
        campaign_code, preview = _offer_payload()
    except (ValidationError, ValueError) as exc:
        return jsonify(error=str(exc)), 422
    preview["mode"] = "demo" if current_app.config["SIGOC_DEMO_MODE"] else "oracle"
    preview["write_enabled"] = current_app.config["DWO_WRITE_ENABLED"]
    audit("offer.preview", "success", _correlation_id(), user=g.user, campaign=campaign_code,
          details=preview["counts"])
    session["last_preview"] = {"campaign": campaign_code, "fingerprint": _fingerprint(preview["operations"])}
    return jsonify(preview)


@bp.post("/api/ofertas/guardar")
@roles_required("editor", "administrador")
def save_offer():
    try:
        campaign_code, preview = _offer_payload()
    except (ValidationError, ValueError) as exc:
        return jsonify(error=str(exc)), 422
    last = session.get("last_preview") or {}
    if last.get("campaign") != campaign_code or last.get("fingerprint") != _fingerprint(preview["operations"]):
        return jsonify(error="La oferta cambió. Genera una nueva vista previa antes de guardar."), 409
    if not current_app.config["SIGOC_DEMO_MODE"] and not all(
        current_app.config[name] for name in (
            "DWO_WRITE_ENABLED", "DWO_MAPPING_VERIFIED", "DWO_BUSINESS_RULES_VERIFIED", "DWO_KEY_VERIFIED"
        )
    ):
        return jsonify(error="La escritura DWO está bloqueada hasta completar las validaciones corporativas."), 403
    try:
        result = _repo("dwo").apply_batch(preview["operations"])
    except (PermissionError, RuntimeError) as exc:
        return jsonify(error=str(exc)), 403
    audit("offer.save", "success", _correlation_id(), user=g.user, campaign=campaign_code, details=result)
    session.pop("last_preview", None)
    return jsonify(result=result, committed=not current_app.config["SIGOC_DEMO_MODE"], mode="demo" if current_app.config["SIGOC_DEMO_MODE"] else "oracle")


@bp.get("/api/ofertas")
@login_required
def offers():
    try:
        page = max(int(request.args.get("page", "1")), 1)
    except ValueError:
        return jsonify(error="Número de página inválido"), 400
    query = request.args.get("q", "")[:100]
    state = request.args.get("state", "")[:40]
    try:
        rows = _repo("dwo").list_offers(query, state, page, 20)
    except Exception:
        current_app.logger.exception("No se pudo consultar DWO")
        return jsonify(error="No se pudo consultar DWO. Verifica la conexión y las credenciales."), 503
    return jsonify(rows=rows, page=page, mode="demo" if current_app.config["SIGOC_DEMO_MODE"] else "oracle")


@bp.patch("/api/ofertas/<path:key>/vigencia")
@roles_required("editor", "administrador")
def update_validity(key):
    payload = request.get_json(silent=True) or {}
    try:
        row = _repo("dwo").update_validity(key, payload.get("starts_on", ""), payload.get("ends_on", ""))
    except (ValueError, KeyError, RuntimeError, PermissionError) as exc:
        return jsonify(error=str(exc)), 422
    audit("offer.validity", "success", _correlation_id(), user=g.user, record_key=key)
    return jsonify(row=row)


@bp.patch("/api/ofertas/<path:key>/estado")
@roles_required("editor", "administrador")
def update_state(key):
    payload = request.get_json(silent=True) or {}
    try:
        row = _repo("dwo").update_state(key, payload.get("state", ""))
    except (ValueError, KeyError, RuntimeError, PermissionError) as exc:
        return jsonify(error=str(exc)), 422
    audit("offer.state", "success", _correlation_id(), user=g.user, record_key=key)
    return jsonify(row=row)


def _fingerprint(operations):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(operations, sort_keys=True).encode()).hexdigest()

