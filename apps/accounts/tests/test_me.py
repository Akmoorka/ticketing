import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

ME = "/api/v1/me/"
LOGIN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"
ORGS = "/api/v1/organizations/"
PASSWORD = "Str0ng-pass-phrase-2026"
CREDS = {"email": "ann@example.com", "password": PASSWORD}


@pytest.fixture
def user():
    u = User.objects.create_user(email="ann@example.com", password=PASSWORD)
    u.email_verified_at = timezone.now()
    u.is_staff = True
    u.save(update_fields=["email_verified_at", "is_staff"])
    return u


def test_delete_me_anonymizes_and_ends_all_sessions(user):
    api = APIClient()
    tokens = api.post(LOGIN, CREDS, format="json").json()
    auth = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}
    assert api.delete(ME, **auth).status_code == 204
    user.refresh_from_db()
    assert user.email == f"deleted-{user.pk}@anonymized.invalid"
    assert not user.is_active and not user.is_staff and not user.has_usable_password()
    assert user.anonymized_at is not None and user.email_verified_at is None
    assert api.post(REFRESH, {"refresh": tokens["refresh"]}, format="json").status_code == 401
    assert api.post(ORGS, {"name": "A", "slug": "a"}, format="json", **auth).status_code == 401
    assert api.post(LOGIN, CREDS, format="json").status_code == 401


def test_future_tickets_block_deletion_with_409(user, settings):
    settings.USER_HAS_FUTURE_TICKETS_CHECKS = ["apps.accounts.tests.blockers.always_blocked"]
    api = APIClient()
    api.force_authenticate(user)
    r = api.delete(ME)
    assert r.status_code == 409 and r.json()["code"] == "has_future_tickets"
    user.refresh_from_db()
    assert user.is_active and user.email == "ann@example.com"


def test_passing_checks_allow_deletion(user, settings):
    settings.USER_HAS_FUTURE_TICKETS_CHECKS = ["apps.accounts.tests.blockers.never_blocked"]
    api = APIClient()
    api.force_authenticate(user)
    assert api.delete(ME).status_code == 204


def test_anonymous_cannot_delete():
    assert APIClient().delete(ME).status_code == 401


def test_email_can_be_registered_again_after_deletion(user):
    api = APIClient()
    api.force_authenticate(user)
    assert api.delete(ME).status_code == 204
    new = services.user_register(email="ann@example.com", password=PASSWORD)
    assert new.pk != user.pk
