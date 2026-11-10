import logging

from apps.common.log_filters import RequestIdFilter
from apps.common.request_id import reset_request_id, set_request_id


def test_generates_request_id(client):
    response = client.get("/health/live/")
    assert len(response["X-Request-ID"]) == 32


def test_keeps_safe_incoming_request_id(client):
    response = client.get("/health/live/", headers={"X-Request-ID": "abc-123"})
    assert response["X-Request-ID"] == "abc-123"


def test_replaces_unsafe_incoming_request_id(client):
    response = client.get("/health/live/", headers={"X-Request-ID": "bad id <x>"})
    assert response["X-Request-ID"] != "bad id <x>"
    assert len(response["X-Request-ID"]) == 32


def test_log_filter_adds_request_id():
    token = set_request_id("rid-1")
    try:
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
        RequestIdFilter().filter(record)
    finally:
        reset_request_id(token)
    assert record.request_id == "rid-1"
