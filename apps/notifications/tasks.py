import smtplib

from celery import shared_task


@shared_task(
    acks_late=True,
    autoretry_for=(OSError, smtplib.SMTPException),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
    soft_time_limit=30,
)
def deliver_email_task(email_id):
    from .services import deliver_email  # импорт внутри: services импортирует tasks

    deliver_email(email_id)
