import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations import services
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-phrase-2026"


def make_user(email):
    return get_user_model().objects.create_user(email=email, password=PASSWORD)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def member_url(org_id, user_id):
    return f"/api/v1/organizations/{org_id}/members/{user_id}/"


@pytest.fixture
def owner():
    return make_user("owner@example.com")


@pytest.fixture
def org(owner):
    return services.organization_create(user=owner, name="Театр", slug="teatr")


@pytest.fixture
def manager(org):
    user = make_user("m@example.com")
    Membership.objects.create(user=user, organization=org, role="manager")
    return user


def test_owner_patches_role(owner, org, manager):
    r = client_for(owner).patch(member_url(org.pk, manager.pk), {"role": "checker"}, format="json")
    assert r.status_code == 200 and r.json() == {"user_id": manager.pk, "role": "checker"}


def test_patch_ignores_extra_fields(owner, org, manager):
    body = {"role": "checker", "user_id": 999, "organization": 5}
    r = client_for(owner).patch(member_url(org.pk, manager.pk), body, format="json")
    assert r.status_code == 200 and r.json()["user_id"] == manager.pk


def test_owner_deletes_member(owner, org, manager):
    r = client_for(owner).delete(member_url(org.pk, manager.pk))
    assert r.status_code == 204
    assert not Membership.objects.filter(user=manager).exists()


def test_last_owner_gives_409_with_code(owner, org):
    api = client_for(owner)
    r = api.patch(member_url(org.pk, owner.pk), {"role": "manager"}, format="json")
    assert r.status_code == 409 and r.json()["code"] == "last_owner"
    r = api.delete(member_url(org.pk, owner.pk))
    assert r.status_code == 409 and r.json()["code"] == "last_owner"


def test_manager_gets_403_outsider_404_anonymous_401(owner, org, manager):
    url = member_url(org.pk, owner.pk)
    assert client_for(manager).patch(url, {"role": "checker"}, format="json").status_code == 403
    assert client_for(manager).delete(url).status_code == 403
    outsider = make_user("o@example.com")
    assert client_for(outsider).patch(url, {"role": "checker"}, format="json").status_code == 404
    assert client_for(outsider).delete(url).status_code == 404
    assert APIClient().delete(url).status_code == 401


def test_unknown_user_is_404(owner, org):
    r = client_for(owner).delete(member_url(org.pk, 999999))
    assert r.status_code == 404


@pytest.mark.parametrize("role", [None, "", "admin", 5, ["owner"]])
def test_garbage_role_is_400(owner, org, manager, role):
    r = client_for(owner).patch(member_url(org.pk, manager.pk), {"role": role}, format="json")
    assert r.status_code == 400


@pytest.mark.parametrize(
    "org_id,user_id",
    [
        ("abc", "1"),
        ("1", "abc"),
        ("99999999999999999999999", "1"),
        ("1", "99999999999999999999999"),
        ("-1", "-1"),
    ],
)
def test_garbage_ids_in_url_are_404_not_500(owner, org_id, user_id):
    api = client_for(owner)
    assert api.patch(member_url(org_id, user_id), {"role": "checker"}, format="json").status_code == 404
    assert api.delete(member_url(org_id, user_id)).status_code == 404
