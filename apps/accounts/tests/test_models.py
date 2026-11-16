import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

User = get_user_model()
pytestmark = pytest.mark.django_db


def test_create_user_lowercases_email_and_hashes_password():
    user = User.objects.create_user("Anna@Example.COM", "s3cret-pass")
    assert user.email == "anna@example.com"
    assert user.password != "s3cret-pass"
    assert user.check_password("s3cret-pass")
    assert not user.is_staff and not user.is_email_verified


def test_email_is_unique_regardless_of_case():
    User.objects.create_user("a@example.com", "s3cret-pass")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user("A@EXAMPLE.com", "s3cret-pass")


def test_email_is_required():
    with pytest.raises(ValueError):
        User.objects.create_user("", "s3cret-pass")


def test_superuser_is_staff_and_verified():
    user = User.objects.create_superuser("root@example.com", "s3cret-pass")
    assert user.is_staff and user.is_superuser and user.is_email_verified
