import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.organizations import services
from apps.organizations.exceptions import SlugTaken
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(
        email="ann@example.com", password="Str0ng-pass-phrase-2026"
    )


def test_create_makes_pending_org_and_owner_membership(user):
    org = services.organization_create(user=user, name="  Театр  ", slug="Teatr")
    assert org.status == Organization.Status.PENDING
    assert org.name == "Театр" and org.slug == "teatr"
    m = Membership.objects.get(organization=org)
    assert m.user == user and m.role == Membership.Role.OWNER


def test_slug_is_unique_case_insensitively(user):
    services.organization_create(user=user, name="A", slug="teatr")
    with pytest.raises(SlugTaken):
        services.organization_create(user=user, name="B", slug="TEATR")
    assert Organization.objects.count() == 1


def test_user_can_be_member_of_one_org_only_once(user):
    org = services.organization_create(user=user, name="A", slug="a")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Membership.objects.create(user=user, organization=org, role="manager")
