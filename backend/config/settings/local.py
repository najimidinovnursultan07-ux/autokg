import sys

from .base import *


DEBUG = True
SECRET_KEY = SECRET_KEY or "local-only-insecure-key-do-not-use-in-production"
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "testserver"]))
LOCAL_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
CORS_ALLOWED_ORIGINS = list(
    dict.fromkeys(
        [*LOCAL_FRONTEND_ORIGINS, *env.list("CORS_ALLOWED_ORIGINS", default=[])]
    )
)
CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        [*LOCAL_FRONTEND_ORIGINS, *env.list("CSRF_TRUSTED_ORIGINS", default=[])]
    )
)
EMAIL_BACKEND = (
    "apps.common.email_backends.BrevoEmailBackend"
    if BREVO_API_KEY
    else env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
)
PASSWORD_RESET_URL = env(
    "PASSWORD_RESET_URL",
    default="http://localhost:5173/password-reset",
)

# Тесты (manage.py test) не должны слать настоящие письма и сообщения в Telegram,
# даже если в .env лежат боевые ключи.
if sys.argv[1:2] == ["test"]:
    TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_ADMIN_TOKEN = TELEGRAM_ADMIN_CHAT_ID = TELEGRAM_ADMIN_2FA_CHAT_ID = ""
    TELEGRAM_ALERTS_BOT_TOKEN = TELEGRAM_ALERTS_BOT_USERNAME = ""
    ALERTS_RUN_INLINE = True  # без фоновых потоков в тестах
    BREVO_API_KEY = ""
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
