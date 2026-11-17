def test_campaign_search(logged_client):
    response = logged_client.get("/api/campanas/3504")
    assert response.status_code == 200
    assert response.json["campaign"]["code"] == "3504"
    assert len(response.json["records"]) == 3


def test_invalid_campaign_rejected(logged_client):
    assert logged_client.get("/api/campanas/35%20OR%201=1").status_code == 400


def test_preview_then_save_demo(logged_client, csrf):
    payload = {"campaign": "3504", "selected_keys": ["PL100-3504-1002"], "discount_type": "fixed", "discount_value": "10", "period": 12}
    headers = {"X-CSRF-Token": csrf}
    preview = logged_client.post("/api/ofertas/previsualizar", json=payload, headers=headers)
    assert preview.status_code == 200
    saved = logged_client.post("/api/ofertas/guardar", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json["mode"] == "demo"
    assert saved.json["committed"] is False


def test_save_requires_preview(logged_client, csrf):
    payload = {"campaign": "356", "selected_keys": ["PL356-356-3561"], "discount_type": "fixed", "discount_value": "10", "period": 12}
    response = logged_client.post("/api/ofertas/guardar", json=payload, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 409


def test_state_update_demo(logged_client, csrf):
    response = logged_client.patch("/api/ofertas/PL100-3504-1001/estado", json={"state": "INACTIVO"}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 200
    assert response.json["row"]["estado_np"] == "INACTIVO"


def test_invalid_page_is_controlled(logged_client):
    response = logged_client.get("/api/ofertas?page=abc")
    assert response.status_code == 400
    assert response.json["error"] == "Número de página inválido"


def test_dwo_connection_error_is_controlled(logged_client):
    class BrokenDWO:
        def list_offers(self, *_args, **_kwargs):
            raise RuntimeError("ORA-01017")

    original = logged_client.application.extensions["dwo"]
    logged_client.application.extensions["dwo"] = BrokenDWO()
    try:
        response = logged_client.get("/api/ofertas")
    finally:
        logged_client.application.extensions["dwo"] = original

    assert response.status_code == 503
    assert response.json["error"].startswith("No se pudo consultar DWO")

