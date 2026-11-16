class FakeEmailSender:
    """Фейк для тестов: письма копятся в списке, наружу ничего не уходит."""

    sent = []

    def send(self, *, to, subject, body):
        type(self).sent.append({"to": to, "subject": subject, "body": body})
