from rest_framework.test import APIClient


def test_validation_error_uses_envelope():
    r = APIClient().post("/api/v1/auth/register/", {}, format="json")
    body = r.json()
    assert r.status_code == 400
    assert set(body) == {"message", "code", "extra"}
    assert body["code"] == "validation_error"
    assert "email" in body["extra"]["errors"]


def test_bad_refresh_token_uses_envelope():
    r = APIClient().post("/api/v1/auth/token/refresh/", {"refresh": "abc"}, format="json")
    assert r.status_code == 401
    assert set(r.json()) == {"message", "code", "extra"}
