import pytest

from apps.common import views


def test_live_is_ok(client):
    response = client.get("/health/live/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_also_under_api_prefix(client):
    assert client.get("/api/v1/health/live/").status_code == 200


@pytest.mark.django_db
def test_ready_ok_when_db_and_redis_up(client, monkeypatch):
    monkeypatch.setattr(views, "check_redis", lambda: None)
    response = client.get("/health/ready/")
    assert response.status_code == 200
    assert response.json()["checks"] == {"db": "ok", "redis": "ok"}


@pytest.mark.django_db
def test_ready_503_when_redis_down_without_leaking_details(client, monkeypatch):
    def boom():
        raise ConnectionError("secret redis host")

    monkeypatch.setattr(views, "check_redis", boom)
    response = client.get("/health/ready/")
    assert response.status_code == 503
    assert response.json()["checks"] == {"db": "ok", "redis": "fail"}
    assert "secret redis host" not in response.content.decode()
