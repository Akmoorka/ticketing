import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations import services
from apps.organizations.models import Invitation, Membership

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-phrase-2026"


def make_user(email):
    return get_user_model().objects.create_user(email=email, password=PASSWORD)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def alice_org():
    alice = make_user("alice@example.com")
    return alice, services.organization_create(user=alice, name="A", slug="a-org")


@pytest.fixture
def bob_client():
    bob = make_user("bob@example.com")
    services.organization_create(user=bob, name="B", slug="b-org")
    return client_for(bob)


def calls(org_id, user_id):
    base = f"/api/v1/organizations/{org_id}"
    return [
        ("post", f"{base}/invitations/", {"email": "x@example.com", "role": "checker"}),
        ("patch", f"{base}/members/{user_id}/", {"role": "checker"}),
        ("delete", f"{base}/members/{user_id}/", None),
    ]


def send(client, method, url, body):
    call = getattr(client, method)
    return call(url, body, format="json") if body is not None else call(url)


def test_foreign_org_is_404_for_every_action_and_nothing_changes(alice_org, bob_client):
    alice, org = alice_org
    for method, url, body in calls(org.pk, alice.pk):
        assert send(bob_client, method, url, body).status_code == 404
    assert Membership.objects.get(organization=org, user=alice).role == "owner"
    assert Membership.objects.filter(organization=org).count() == 1
    assert Invitation.objects.count() == 0


def test_foreign_org_looks_exactly_like_a_missing_one(alice_org, bob_client):
    alice, org = alice_org
    foreign = calls(org.pk, alice.pk)
    missing = calls(999999, alice.pk)
    for (method, url, body), (_, missing_url, _) in zip(foreign, missing):
        a = send(bob_client, method, url, body)
        b = send(bob_client, method, missing_url, body)
        assert a.status_code == b.status_code == 404
        assert a.json() == b.json()
