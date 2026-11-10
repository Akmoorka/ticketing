import logging

from .request_id import get_request_id


class RequestIdFilter(logging.Filter):
    """Добавляет request_id в каждую строку лога."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True
