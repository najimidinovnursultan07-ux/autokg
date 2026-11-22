from django.core.exceptions import ImproperlyConfigured

from .base import *


DEBUG = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
INSTALLED_APPS += ["cloudinary_storage", "cloudinary"]
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Render стоит за Cloudflare: CF-Connecting-IP подделать нельзя, X-Forwarded-For — можно
CLIENT_IP_HEADER = env("CLIENT_IP_HEADER", default="CF-Connecting-IP")

# Фронтенд переехал на autobuy-kg.vercel.app. Новый домен разрешён всегда,
# старый autokg-ten.vercel.app отключён — даже если он остался в переменных Render.
FRONTEND_ORIGIN = "https://autobuy-kg.vercel.app"
OLD_FRONTEND_ORIGIN = "https://autokg-ten.vercel.app"


def _with_frontend(origins):
    origins = [o.rstrip("/") for o in origins if o.rstrip("/") != OLD_FRONTEND_ORIGIN]
    return list(dict.fromkeys([FRONTEND_ORIGIN, *origins]))


CORS_ALLOWED_ORIGINS = _with_frontend(CORS_ALLOWED_ORIGINS)
CSRF_TRUSTED_ORIGINS = _with_frontend(CSRF_TRUSTED_ORIGINS)
if not PASSWORD_RESET_URL or PASSWORD_RESET_URL.startswith(OLD_FRONTEND_ORIGIN):
    PASSWORD_RESET_URL = f"{FRONTEND_ORIGIN}/password-reset"
if not FRONTEND_URL or FRONTEND_URL.rstrip("/") == OLD_FRONTEND_ORIGIN:
    FRONTEND_URL = FRONTEND_ORIGIN
# Фронт (vercel.app) и API (onrender.com) — разные сайты: refresh-cookie
# должна быть SameSite=None, иначе браузер её не отправит и сессия слетит.
AUTH_COOKIE_SAMESITE = "None"

if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be configured in production.")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured in production.")
if "postgresql" not in DATABASES["default"]["ENGINE"]:
    raise ImproperlyConfigured("Production must use PostgreSQL.")
if not PASSWORD_RESET_URL.startswith("https://"):
    raise ImproperlyConfigured(
        "PASSWORD_RESET_URL must be an HTTPS frontend URL in production."
    )
if not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "Configure CORS_ALLOWED_ORIGINS with the trusted frontend origins."
    )
if not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured(
        "Configure CSRF_TRUSTED_ORIGINS with the trusted frontend origins."
    )
if EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend" or not EMAIL_HOST:
    raise ImproperlyConfigured(
        "Configure an SMTP email backend and EMAIL_HOST in production."
    )

# Render терминирует TLS на балансировщике и передаёт X-Forwarded-Proto
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^api/health/"]
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_PATH = "/"
SESSION_COOKIE_SAMESITE = "None"
AUTH_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Cloudinary media storage
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": env("CLOUDINARY_API_KEY"),
    "API_SECRET": env("CLOUDINARY_API_SECRET"),
}
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
