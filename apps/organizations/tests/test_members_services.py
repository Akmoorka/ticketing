import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

from apps.organizations import services
from apps.organizations.exceptions import (
    LastOwner,
    MemberNotFound,
    OrganizationNotFound,
    RoleNotAllowed,
)
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db
PASSWORD = "Str0ng-pass-phrase-2026"
AuditEntry = apps.get_model("audit", "AuditEntry")


def make_user(email):
    return get_user_model().objects.create_user(email=email, password=PASSWORD)


@pytest.fixture
def owner():
    return make_user("owner@example.com")


@pytest.fixture
def org(owner):
    return services.organization_create(user=owner, name="Театр", slug="teatr")


def add_member(org, email, role):
    user = make_user(email)
    Membership.objects.create(user=user, organization=org, role=role)
    return user


def change(actor, org, user, role):
    return services.member_change_role(
        actor=actor, organization_id=org.pk, user_id=user.pk, role=role
    )


def remove(actor, org, user):
    return services.member_remove(actor=actor, organization_id=org.pk, user_id=user.pk)


def test_owner_changes_role_and_it_is_audited(owner, org):
    manager = add_member(org, "m@example.com", "manager")
    assert change(owner, org, manager, "checker").role == "checker"
    entry = AuditEntry.objects.get(action="member.role_changed")
    assert entry.actor == owner
    assert entry.data["from"] == "manager" and entry.data["to"] == "checker"


def test_same_role_is_noop_without_audit(owner, org):
    manager = add_member(org, "m@example.com", "manager")
    change(owner, org, manager, "manager")
    assert AuditEntry.objects.count() == 0


def test_non_owner_forbidden_and_outsider_sees_404(owner, org):
    manager = add_member(org, "m@example.com", "manager")
    with pytest.raises(RoleNotAllowed):
        change(manager, org, owner, "checker")
    with pytest.raises(RoleNotAllowed):
        remove(manager, org, owner)
    outsider = make_user("o@example.com")
    with pytest.raises(OrganizationNotFound):
        change(outsider, org, manager, "checker")
    with pytest.raises(OrganizationNotFound):
        remove(outsider, org, manager)


def test_unknown_member_is_not_found(owner, org):
    stranger = make_user("s@example.com")
    with pytest.raises(MemberNotFound):
        change(owner, org, stranger, "checker")
    with pytest.raises(MemberNotFound):
        remove(owner, org, stranger)


def test_last_owner_cannot_be_demoted_or_removed(owner, org):
    with pytest.raises(LastOwner):
        change(owner, org, owner, "manager")
    with pytest.raises(LastOwner):
        remove(owner, org, owner)
    assert Membership.objects.get(user=owner, organization=org).role == "owner"
    assert AuditEntry.objects.count() == 0


def test_with_second_owner_demotion_and_removal_are_allowed(owner, org):
    second = add_member(org, "second@example.com", "owner")
    change(second, org, owner, "manager")
    assert Membership.objects.get(user=owner, organization=org).role == "manager"
    third = add_member(org, "third@example.com", "owner")
    remove(third, org, second)
    assert not Membership.objects.filter(user=second, organization=org).exists()


def test_remove_deletes_membership_and_audits(owner, org):
    checker = add_member(org, "c@example.com", "checker")
    remove(owner, org, checker)
    assert not Membership.objects.filter(user=checker, organization=org).exists()
    entry = AuditEntry.objects.get(action="member.removed")
    assert entry.data["user_id"] == checker.pk and entry.data["role"] == "checker"
