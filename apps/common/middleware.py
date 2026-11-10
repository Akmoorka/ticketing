import logging
import re
import time

from .request_id import new_request_id, reset_request_id, set_request_id

HEADER = "X-Request-ID"
# Чужой id принимаем только если он безопасен для логов
VALID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
logger = logging.getLogger("apps.common.requests")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if VALID.match(incoming) else new_request_id()
        request.request_id = request_id
        token = set_request_id(request_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response[HEADER] = request_id
            elapsed_ms = int((time.monotonic() - started) * 1000)
            # query string не логируем: в ней может быть email
            logger.info(
                "%s %s -> %s %sms",
                request.method, request.path, response.status_code, elapsed_ms,
            )
            return response
        finally:
            reset_request_id(token)
