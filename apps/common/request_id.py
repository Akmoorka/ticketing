import contextvars
import uuid

_request_id = contextvars.ContextVar("request_id", default="-")


def new_request_id():
    return uuid.uuid4().hex


def get_request_id():
    return _request_id.get()


def set_request_id(value):
    return _request_id.set(value)


def reset_request_id(token):
    _request_id.reset(token)
