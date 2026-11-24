import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework.test import APIClient

from apps.organizations import services
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-phrase-2026"


@pytest.fixture(autouse=True)
def outbox():
    sent = import_string(settings.EMAIL_SENDER).sent
    sent.clear()
    yield sent
    sent.clear()


def make_user(email, verified=True):
    user = get_user_model().objects.create_user(email=email, password=PASSWORD)
    if verified:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
    return user


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def owner():
    return make_user("owner@example.com")


@pytest.fixture
def org(owner):
    return services.organization_create(user=owner, name="Театр", slug="teatr")


def inv_url(org_id):
    return f"/api/v1/organizations/{org_id}/invitations/"


def test_owner_creates_invitation_response_has_no_token(
    owner, org, outbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        r = client_for(owner).post(
            inv_url(org.pk), {"email": "guest@example.com", "role": "manager"}, format="json"
        )
    assert r.status_code == 201
    assert set(r.json()) == {"id", "email", "role", "expires_at"}
    assert outbox[0]["body"].splitlines()[2] not in r.content.decode()


def test_manager_gets_403_outsider_gets_404_anonymous_gets_401(org):
    manager = make_user("m@example.com")
    Membership.objects.create(user=manager, organization=org, role="manager")
    body = {"email": "x@example.com", "role": "checker"}
    assert client_for(manager).post(inv_url(org.pk), body, format="json").status_code == 403
    outsider = make_user("o@example.com")
    assert client_for(outsider).post(inv_url(org.pk), body, format="json").status_code == 404
    assert APIClient().post(inv_url(org.pk), body, format="json").status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "x@example.com", "role": "admin"},
        {"email": "x@example.com", "role": None},
        {"email": "not-an-email", "role": "manager"},
        {"email": ["x@example.com"], "role": "manager"},
    ],
)
def test_invitation_garbage_is_400(owner, org, payload):
    assert client_for(owner).post(inv_url(org.pk), payload, format="json").status_code == 400


@pytest.mark.parametrize("org_id", ["abc", "99999999999999999999999999", "-1", "0"])
def test_garbage_org_id_in_url_is_404_not_500(owner, org_id):
    body = {"email": "x@example.com", "role": "checker"}
    assert client_for(owner).post(inv_url(org_id), body, format="json").status_code == 404


def invite_guest(owner, org, commit_cb):
    with commit_cb(execute=True):
        client_for(owner).post(
            inv_url(org.pk), {"email": "guest@example.com", "role": "checker"}, format="json"
        )


def test_accept_flow_through_api(owner, org, outbox, django_capture_on_commit_callbacks):
    invite_guest(owner, org, django_capture_on_commit_callbacks)
    token = outbox[0]["body"].splitlines()[2]
    guest = client_for(make_user("guest@example.com"))
    r = guest.post(f"/api/v1/invitations/{token}/accept/")
    assert r.status_code == 200
    assert r.json() == {"organization_id": org.pk, "role": "checker"}
    assert guest.post(f"/api/v1/invitations/{token}/accept/").status_code == 400


def test_accept_with_other_email_is_403(owner, org, outbox, django_capture_on_commit_callbacks):
    invite_guest(owner, org, django_capture_on_commit_callbacks)
    token = outbox[0]["body"].splitlines()[2]
    other = client_for(make_user("other@example.com"))
    assert other.post(f"/api/v1/invitations/{token}/accept/").status_code == 403


@pytest.mark.parametrize("token", ["abc", "a%00b", "x" * 3000])
def test_accept_garbage_token_is_400(token):
    guest = client_for(make_user("guest@example.com"))
    assert guest.post(f"/api/v1/invitations/{token}/accept/").status_code == 400


def test_accept_requires_login():
    assert APIClient().post("/api/v1/invitations/abc/accept/").status_code == 401
