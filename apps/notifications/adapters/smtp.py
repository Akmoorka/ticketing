from django.core.mail import send_mail


class SmtpEmailSender:
    """Боевой адаптер: письма идут через настроенный в MAILERS SMTP (Mailpit в dev)."""

    def send(self, *, to, subject, body):
        send_mail(subject, body, None, [to], fail_silently=False)
