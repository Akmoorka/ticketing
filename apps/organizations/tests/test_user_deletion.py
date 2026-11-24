import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.organizations import services
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db


def test_membership_survives_user_anonymization():
    user = get_user_model().objects.create_user(
        email="ann@example.com", password="Str0ng-pass-phrase-2026"
    )
    org = services.organization_create(user=user, name="Театр", slug="teatr")
    api = APIClient()
    api.force_authenticate(user)
    assert api.delete("/api/v1/me/").status_code == 204
    membership = Membership.objects.get(organization=org)
    assert membership.user_id == user.pk and membership.role == "owner"
