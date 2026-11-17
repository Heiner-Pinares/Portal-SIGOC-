from app.services.auth import classify_identity


def test_login_and_logout(client):
    page = client.get("/login")
    token = page.text.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    response = client.post("/login", data={"identity": "editor", "password": "secret123", "csrf_token": token})
    assert response.status_code == 302
    assert client.get("/").status_code == 200


def test_bad_csrf_is_rejected(client):
    response = client.post("/login", data={"identity": "editor", "password": "secret123"})
    assert response.status_code == 400


def test_corporate_identity_never_falls_back_local(app):
    with app.test_request_context():
        assert classify_identity("C27826") == ("corporate_code", "C27826")
        assert classify_identity("c27826@claro.com.pe") == ("corporate_code", "C27826")
        assert classify_identity("nombre.apellido@claro.com.pe")[0] == "corporate_email"
        assert classify_identity("editor") == ("local", "editor")


def test_unauthenticated_api_is_rejected(client):
    response = client.get("/api/campanas/3504")
    assert response.status_code == 401

