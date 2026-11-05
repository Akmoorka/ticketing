import os

from .base import *  # noqa: F401,F403

DEBUG = True
SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-insecure-key-do-not-use-in-prod"
