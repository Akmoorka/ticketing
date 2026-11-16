from django.db import models


class OutgoingEmail(models.Model):
    """Письмо, которое нужно отправить. dedup_key гарантирует: одно письмо — одна запись."""

    dedup_key = models.CharField(max_length=200, unique=True)
    to = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)  # кто-то уже отправляет
    sent_at = models.DateTimeField(null=True, blank=True)
