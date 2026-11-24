import logging

from rest_framework.test import APIClient

from apps.common.middleware import mask_path


def test_mask_path_hides_invitation_token():
    assert mask_path("/api/v1/invitations/abc123/accept/") == "/api/v1/invitations/***/accept/"


def test_mask_path_leaves_other_paths_alone():
    for path in [
        "/api/v1/auth/token/",
        "/api/v1/organizations/5/invitations/",
        "/health/live/",
    ]:
        assert mask_path(path) == path


def test_request_log_does_not_contain_invitation_token(caplog):
    logger = logging.getLogger("apps.common.requests")
    old_level = logger.level
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.INFO)
    try:
        APIClient().post("/api/v1/invitations/SECRETTOKEN123/accept/")
    finally:
        logger.removeHandler(caplog.handler)
        logger.setLevel(old_level)
    text = " ".join(record.getMessage() for record in caplog.records)
    assert "SECRETTOKEN123" not in text
    assert "***" in text
