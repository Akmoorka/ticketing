from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.module_loading import import_string

from apps.organizations import services
from apps.organizations.exceptions import (
    InvalidInvitation,
    InvitationNotForUser,
    OrganizationNotFound,
    RoleNotAllowed,
)
from apps.organizations.models import Invitation, Membership

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


@pytest.fixture
def owner():
    return make_user("owner@example.com")


@pytest.fixture
def org(owner):
    return services.organization_create(user=owner, name="Театр", slug="teatr")


def invite(commit_cb, actor, org, email="guest@example.com", role="manager"):
    with commit_cb(execute=True):
        return services.invitation_create(
            actor=actor, organization_id=org.pk, email=email, role=role
        )


def token_from(outbox):
    return outbox[-1]["body"].splitlines()[2]


def test_owner_invites_token_is_hashed_and_sent_by_email(
    owner, org, outbox, django_capture_on_commit_callbacks
):
    inv = invite(django_capture_on_commit_callbacks, owner, org, email="Guest@Example.com")
    token = token_from(outbox)
    assert inv.email == "guest@example.com"
    assert inv.token_hash == services.hash_token(token) and inv.token_hash != token
    assert not Invitation.objects.filter(token_hash=token).exists()
    assert timedelta(hours=71) < inv.expires_at - timezone.now() <= timedelta(hours=72)
    assert len(outbox) == 1 and outbox[0]["to"] == "guest@example.com"


def test_manager_cannot_invite_and_outsider_sees_404(org):
    manager = make_user("m@example.com")
    Membership.objects.create(user=manager, organization=org, role="manager")
    args = {"email": "x@example.com", "role": "checker"}
    with pytest.raises(RoleNotAllowed):
        services.invitation_create(actor=manager, organization_id=org.pk, **args)
    outsider = make_user("o@example.com")
    with pytest.raises(OrganizationNotFound):
        services.invitation_create(actor=outsider, organization_id=org.pk, **args)
    with pytest.raises(OrganizationNotFound):
        services.invitation_create(actor=outsider, organization_id=999999, **args)


def test_accept_creates_membership_and_token_is_one_time(
    owner, org, outbox, django_capture_on_commit_callbacks
):
    invite(django_capture_on_commit_callbacks, owner, org, role="checker")
    token = token_from(outbox)
    guest = make_user("guest@example.com")
    m = services.invitation_accept(user=guest, token=token)
    assert m.organization == org and m.role == "checker"
    with pytest.raises(InvalidInvitation):
        services.invitation_accept(user=guest, token=token)


def test_expired_invitation_is_rejected(owner, org, outbox, django_capture_on_commit_callbacks):
    inv = invite(django_capture_on_commit_callbacks, owner, org)
    past = timezone.now() - timedelta(seconds=1)
    Invitation.objects.filter(pk=inv.pk).update(expires_at=past)
    with pytest.raises(InvalidInvitation):
        services.invitation_accept(user=make_user("guest@example.com"), token=token_from(outbox))


def test_wrong_or_unverified_email_is_rejected_and_token_survives(
    owner, org, outbox, django_capture_on_commit_callbacks
):
    invite(django_capture_on_commit_callbacks, owner, org)
    token = token_from(outbox)
    with pytest.raises(InvitationNotForUser):
        services.invitation_accept(user=make_user("other@example.com"), token=token)
    unverified = make_user("guest@example.com", verified=False)
    with pytest.raises(InvitationNotForUser):
        services.invitation_accept(user=unverified, token=token)
    assert Membership.objects.filter(organization=org).count() == 1


def test_garbage_tokens_are_rejected():
    user = make_user("guest@example.com")
    for bad in ["", "abc", "a\x00b", "x" * 5000]:
        with pytest.raises(InvalidInvitation):
            services.invitation_accept(user=user, token=bad)
