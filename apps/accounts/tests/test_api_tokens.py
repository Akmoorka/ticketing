import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
LOGOUT = "/api/v1/auth/logout/"
REGISTER = "/api/v1/auth/register/"
PASSWORD = "Str0ng-pass-phrase-2026"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(email="ann@example.com", password=PASSWORD)


def login(api, email="ann@example.com", password=PASSWORD, **extra):
    return api.post(LOGIN, {"email": email, "password": password}, format="json", **extra)


def test_login_returns_token_pair(api, user):
    r = login(api, email="ANN@Example.com")
    assert r.status_code == 200
    assert set(r.json()) == {"access", "refresh"}


def test_wrong_password_and_unknown_email_look_the_same(api, user):
    a = login(api, password="wrong")
    b = login(api, email="nobody@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_inactive_user_cannot_login(api, user):
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert login(api).status_code == 401


def test_five_failures_block_even_correct_password(api, user):
    for _ in range(5):
        assert login(api, password="wrong").status_code == 401
    assert login(api, password="wrong").status_code == 429
    assert login(api).status_code == 429


def test_lock_is_per_ip_and_email(api, user):
    for _ in range(5):
        login(api, password="wrong")
    assert login(api, REMOTE_ADDR="10.0.0.2").status_code == 200
    assert login(api, email="other@example.com").status_code == 401


def test_success_resets_failure_counter(api, user):
    for _ in range(4):
        assert login(api, password="wrong").status_code == 401
    assert login(api).status_code == 200
    for _ in range(4):
        assert login(api, password="wrong").status_code == 401
    assert login(api).status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": None, "password": None},
        {"email": 123, "password": ["x"]},
        {"email": "a\x00b@example.com", "password": "x"},
        {"email": "ann@example.com", "password": "p" * 1000},
        {"email": "x" * 5000, "password": "x"},
    ],
)
def test_login_garbage_input_is_400(api, payload):
    assert api.post(LOGIN, payload, format="json").status_code == 400


def test_refresh_rotates_and_old_token_dies(api, user):
    old = login(api).json()["refresh"]
    r = api.post(REFRESH, {"refresh": old}, format="json")
    assert r.status_code == 200 and r.json()["refresh"] != old
    assert api.post(REFRESH, {"refresh": old}, format="json").status_code == 401


def test_logout_revokes_refresh_token(api, user):
    refresh = login(api).json()["refresh"]
    assert api.post(LOGOUT, {"refresh": refresh}, format="json").status_code == 204
    assert api.post(REFRESH, {"refresh": refresh}, format="json").status_code == 401


@pytest.mark.parametrize(
    "payload", [{}, {"refresh": ""}, {"refresh": "abc"}, {"refresh": None}, {"refresh": "a\x00b"}]
)
def test_logout_garbage_is_400(api, payload):
    assert api.post(LOGOUT, payload, format="json").status_code == 400


def test_register_is_limited_to_10_per_hour_per_ip(api):
    for _ in range(10):
        assert api.post(REGISTER, {}, format="json").status_code == 400
    assert api.post(REGISTER, {}, format="json").status_code == 429


def test_throttled_response_has_envelope_and_retry_after(api, user):
    for _ in range(5):
        login(api, password="wrong")
    r = login(api, password="wrong")
    assert r.status_code == 429
    assert r.json()["code"] == "throttled"
    assert r.json()["extra"]["retry_after"] == 300
    assert r["Retry-After"] == "300"


def test_wrong_password_uses_envelope(api, user):
    r = login(api, password="wrong")
    assert r.status_code == 401
    assert r.json()["code"] == "invalid_credentials"
