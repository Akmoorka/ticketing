import pytest
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER = "/api/v1/auth/register/"
VERIFY = "/api/v1/auth/verify-email/"
PASSWORD = "Str0ng-pass-phrase-2026"


@pytest.fixture(autouse=True)
def outbox():
    sent = import_string(settings.EMAIL_SENDER).sent
    sent.clear()
    yield sent
    sent.clear()


@pytest.fixture
def api():
    return APIClient()


def register(api, commit_cb, email="ann@example.com", password=PASSWORD):
    with commit_cb(execute=True):
        return api.post(REGISTER, {"email": email, "password": password}, format="json")


def test_register_returns_201_without_password_and_sends_email(
    api, outbox, django_capture_on_commit_callbacks
):
    r = register(api, django_capture_on_commit_callbacks)
    assert r.status_code == 201
    assert set(r.json()) == {"id", "email"}
    assert len(outbox) == 1


def test_register_duplicate_email_is_400(api, django_capture_on_commit_callbacks):
    register(api, django_capture_on_commit_callbacks)
    r = register(api, django_capture_on_commit_callbacks, email="ANN@example.com")
    assert r.status_code == 400 and "email" in r.json()
    assert User.objects.count() == 1


def test_register_weak_password_is_400(api, django_capture_on_commit_callbacks):
    r = register(api, django_capture_on_commit_callbacks, password="123")
    assert r.status_code == 400 and "password" in r.json()


def test_register_ignores_broken_authorization_header(api, django_capture_on_commit_callbacks):
    api.credentials(HTTP_AUTHORIZATION="Bearer garbage")
    assert register(api, django_capture_on_commit_callbacks).status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": None, "password": None},
        {"email": 123, "password": ["x"]},
        {"email": "not-an-email", "password": PASSWORD},
        {"email": "a" * 300 + "@example.com", "password": PASSWORD},
        {"email": "a\x00b@example.com", "password": PASSWORD},
        {"email": "ann@example.com", "password": "p" * 1000},
        {"email": ["a@example.com"], "password": PASSWORD},
    ],
)
def test_register_garbage_input_is_400_not_500(api, payload):
    r = api.post(REGISTER, payload, format="json")
    assert r.status_code == 400
    assert User.objects.count() == 0


def test_register_non_json_body_is_not_500(api):
    r = api.post(REGISTER, "[1, 2", content_type="application/json")
    assert r.status_code == 400


def test_verify_email_flow(api, outbox, django_capture_on_commit_callbacks):
    register(api, django_capture_on_commit_callbacks)
    token = outbox[0]["body"].splitlines()[1]
    r = api.post(VERIFY, {"token": token}, format="json")
    assert r.status_code == 200 and r.json() == {"email_verified": True}
    assert User.objects.get().email_verified_at is not None


@pytest.mark.parametrize("token", ["", "abc", "a\x00b", "x" * 5000, None, 5, ["t"]])
def test_verify_email_garbage_token_is_400(api, token):
    r = api.post(VERIFY, {"token": token}, format="json")
    assert r.status_code == 400
