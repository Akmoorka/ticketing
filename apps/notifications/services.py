from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from .models import OutgoingEmail
from .ports import EmailSender
from .tasks import deliver_email_task


def get_sender() -> EmailSender:
    return import_string(settings.EMAIL_SENDER)()


def queue_email(*, dedup_key, to, subject, body) -> int:
    """Записать письмо в БД (в транзакции вызывающего) и отправить после коммита.

    Повтор с тем же dedup_key новой записи не создаёт.
    """
    email, _ = OutgoingEmail.objects.get_or_create(
        dedup_key=dedup_key,
        defaults={"to": to, "subject": subject, "body": body},
    )
    transaction.on_commit(lambda: deliver_email_task.delay(email.pk), robust=True)
    return email.pk


def deliver_email(email_id) -> bool:
    """Отправить письмо ровно одним исполнителем. True, если отправили мы."""
    claimed = OutgoingEmail.objects.filter(
        pk=email_id, sent_at__isnull=True, claimed_at__isnull=True
    ).update(claimed_at=timezone.now())
    if not claimed:
        return False  # уже отправлено или отправляется другим воркером
    email = OutgoingEmail.objects.get(pk=email_id)
    try:
        get_sender().send(to=email.to, subject=email.subject, body=email.body)
    except Exception:
        # отпускаем письмо, чтобы повтор мог его отправить; ошибку не глушим
        OutgoingEmail.objects.filter(pk=email_id).update(claimed_at=None)
        raise
    OutgoingEmail.objects.filter(pk=email_id).update(sent_at=timezone.now())
    return True
