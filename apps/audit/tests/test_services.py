import pytest
from django.contrib.auth import get_user_model

from apps.audit import services
from apps.audit.models import AuditEntry

pytestmark = pytest.mark.django_db


def test_record_stores_who_what_and_data():
    user = get_user_model().objects.create_user(email="a@example.com", password="Str0ng-pass-2026")
    entry = services.record(
        actor=user, action="x.done", object_type="thing", object_id=7, data={"k": "v"}
    )
    saved = AuditEntry.objects.get(pk=entry.pk)
    assert saved.actor == user and saved.action == "x.done"
    assert saved.object_id == "7" and saved.data == {"k": "v"}
