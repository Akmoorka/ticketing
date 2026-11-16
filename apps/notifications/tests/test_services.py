import pytest

from apps.notifications import services
from apps.notifications.adapters.fake import FakeEmailSender
from apps.notifications.models import OutgoingEmail

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_outbox():
    FakeEmailSender.sent.clear()
    yield
    FakeEmailSender.sent.clear()


def make(key="k1"):
    return services.queue_email(
        dedup_key=key, to="a@example.com", subject="Тема", body="Текст"
    )


def test_same_dedup_key_creates_one_row_and_one_email(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        make()
        make()
    assert OutgoingEmail.objects.count() == 1
    assert len(FakeEmailSender.sent) == 1


def test_second_delivery_is_a_noop(django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        email_id = make()
    assert services.deliver_email(email_id) is False
    assert len(FakeEmailSender.sent) == 1


def test_failed_send_releases_claim_and_retry_succeeds(monkeypatch):
    email_id = make()
    original = FakeEmailSender.send

    def boom(self, **kwargs):
        raise OSError("smtp down")

    monkeypatch.setattr(FakeEmailSender, "send", boom)
    with pytest.raises(OSError):
        services.deliver_email(email_id)
    email = OutgoingEmail.objects.get(pk=email_id)
    assert email.claimed_at is None and email.sent_at is None

    monkeypatch.setattr(FakeEmailSender, "send", original)
    assert services.deliver_email(email_id) is True
    assert len(FakeEmailSender.sent) == 1
