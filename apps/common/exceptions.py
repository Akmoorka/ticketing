from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

STATUS_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    415: "unsupported_media_type",
    429: "throttled",
}


class Conflict(exceptions.APIException):
    """409: операция конфликтует с состоянием (code задаётся при raise, например last_owner)."""

    status_code = 409
    default_detail = "Конфликт состояния."
    default_code = "conflict"


def api_exception_handler(exc, context):
    """Все ошибки API в одном конверте: {"message", "code", "extra"}."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, exceptions.ValidationError):
        body = {
            "message": "Ошибка в данных запроса.",
            "code": "validation_error",
            "extra": {"errors": response.data},
        }
    else:
        codes = exc.get_codes() if isinstance(exc, exceptions.APIException) else None
        code = codes if isinstance(codes, str) else STATUS_CODES.get(response.status_code, "error")
        data = response.data
        message = str(data.get("detail", "")) if isinstance(data, dict) else str(data)
        extra = {}
        if isinstance(exc, exceptions.Throttled) and exc.wait is not None:
            extra["retry_after"] = int(exc.wait)
        body = {"message": message, "code": code, "extra": extra}
    response.data = body
    return response
