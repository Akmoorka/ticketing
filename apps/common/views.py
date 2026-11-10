import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def check_db():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()


def check_redis():
    client = redis.Redis.from_url(
        settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
    )
    try:
        client.ping()
    finally:
        client.close()


def live(request):
    """Процесс жив."""
    return JsonResponse({"status": "ok"})


def ready(request):
    """БД и Redis доступны. Платёжный шлюз сюда не входит: его падение
    ломает только оплату, а не весь сервис (деградация, не падение)."""
    checks = {}
    for name, check in (("db", check_db), ("redis", check_redis)):
        try:
            check()
            checks[name] = "ok"
        except Exception:
            logger.exception("health: проверка %s не прошла", name)
            checks[name] = "fail"
    ok = all(value == "ok" for value in checks.values())
    return JsonResponse(
        {"status": "ok" if ok else "unavailable", "checks": checks},
        status=200 if ok else 503,
    )
