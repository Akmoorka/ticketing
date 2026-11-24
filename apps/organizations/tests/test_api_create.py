import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

URL = "/api/v1/organizations/"


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        email="ann@example.com", password="Str0ng-pass-phrase-2026"
    )


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_anonymous_gets_401():
    r = APIClient().post(URL, {"name": "A", "slug": "a"}, format="json")
    assert r.status_code == 401


def test_create_returns_201_pending_and_makes_creator_owner(api, user):
    r = api.post(URL, {"name": "Театр", "slug": "teatr"}, format="json")
    assert r.status_code == 201
    body = r.json()
    assert set(body) == {"id", "name", "slug", "status"}
    assert body["status"] == "pending"
    m = Membership.objects.get(organization_id=body["id"])
    assert m.user == user and m.role == "owner"


def test_taken_slug_is_400(api):
    api.post(URL, {"name": "A", "slug": "teatr"}, format="json")
    r = api.post(URL, {"name": "B", "slug": "TEATR"}, format="json")
    assert r.status_code == 400 and "slug" in r.json()["extra"]["errors"]
    assert Organization.objects.count() == 1


def test_extra_fields_cannot_change_status(api):
    r = api.post(
        URL, {"name": "A", "slug": "a", "status": "approved", "role": "x"}, format="json"
    )
    assert r.status_code == 201 and r.json()["status"] == "pending"


def test_one_user_can_create_several_organizations(api):
    assert api.post(URL, {"name": "A", "slug": "a"}, format="json").status_code == 201
    assert api.post(URL, {"name": "B", "slug": "b"}, format="json").status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": None, "slug": None},
        {"name": "A", "slug": ""},
        {"name": "A", "slug": "bad slug!"},
        {"name": "A", "slug": "x" * 100},
        {"name": "a\x00b", "slug": "ok"},
        {"name": "n" * 5000, "slug": "ok"},
    ],
)
def test_garbage_input_is_400_not_500(api, payload):
    assert api.post(URL, payload, format="json").status_code == 400
    assert Organization.objects.count() == 0
