import hashlib

from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.throttling import BaseThrottle

LIMIT = 5  # неудачных попыток
WINDOW = 5 * 60  # за 5 минут


def client_ip(request) -> str:
    return BaseThrottle().get_ident(request)  # учитывает NUM_PROXIES за nginx


def _key(ip: str, email: str) -> str:
    raw = f"{ip}|{email}".encode()
    return "login-fail:" + hashlib.sha256(raw).hexdigest()


def check(ip: str, email: str) -> None:
    if cache.get(_key(ip, email), 0) >= LIMIT:
        raise Throttled(wait=WINDOW)


def register_failure(ip: str, email: str) -> None:
    key = _key(ip, email)
    cache.add(key, 0, WINDOW)
    try:
        cache.incr(key)
    except ValueError:  # ключ истёк между add и incr
        cache.set(key, 1, WINDOW)


def reset(ip: str, email: str) -> None:
    cache.delete(_key(ip, email))
