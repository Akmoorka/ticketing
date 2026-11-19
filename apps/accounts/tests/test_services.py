import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string

from apps.accounts import services
from apps.accounts.exceptions import EmailAlreadyRegistered, InvalidVerificationToken
from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-phrase-2026"


@pytest.fixture(autouse=True)
def outbox():
    sent = import_string(settings.EMAIL_SENDER).sent  # fake из test.py
    sent.clear()
    yield sent
    sent.clear()


def register(commit_cb, email="Ann@Example.com"):
    with commit_cb(execute=True):
        return services.user_register(email=email, password=PASSWORD)


def token_from(outbox):
    return outbox[0]["body"].splitlines()[1]


def test_register_creates_unverified_user_and_sends_one_email(
    outbox, django_capture_on_commit_callbacks
):
    user = register(django_capture_on_commit_callbacks)
    assert user.email == "ann@example.com"
    assert user.email_verified_at is None
    assert user.check_password(PASSWORD)
    assert len(outbox) == 1 and outbox[0]["to"] == "ann@example.com"


def test_duplicate_email_is_rejected_case_insensitively(django_capture_on_commit_callbacks):
    register(django_capture_on_commit_callbacks)
    with pytest.raises(EmailAlreadyRegistered):
        services.user_register(email="ANN@example.com", password=PASSWORD)
    assert User.objects.count() == 1


def test_weak_password_is_rejected():
    with pytest.raises(ValidationError):
        services.user_register(email="b@example.com", password="123")
    assert User.objects.count() == 0


def test_verify_email_marks_user_verified_and_is_repeatable(
    outbox, django_capture_on_commit_callbacks
):
    user = register(django_capture_on_commit_callbacks)
    token = token_from(outbox)
    verified = services.verify_email(token=token)
    assert verified.pk == user.pk and verified.email_verified_at is not None
    first = verified.email_verified_at
    assert services.verify_email(token=token).email_verified_at == first


def test_garbage_token_is_rejected():
    for bad in ["", "abc", "a:b:c", "x" * 500]:
        with pytest.raises(InvalidVerificationToken):
            services.verify_email(token=bad)


def test_expired_token_is_rejected(outbox, monkeypatch, django_capture_on_commit_callbacks):
    register(django_capture_on_commit_callbacks)
    monkeypatch.setattr(services, "VERIFICATION_MAX_AGE", -1)
    with pytest.raises(InvalidVerificationToken):
        services.verify_email(token=token_from(outbox))


def test_token_stops_working_after_email_change(outbox, django_capture_on_commit_callbacks):
    user = register(django_capture_on_commit_callbacks)
    token = token_from(outbox)
    user.email = "new@example.com"
    user.save(update_fields=["email"])
    with pytest.raises(InvalidVerificationToken):
        services.verify_email(token=token)
