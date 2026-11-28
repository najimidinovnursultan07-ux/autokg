from datetime import timedelta
from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

env = environ.Env()
env.read_env(PROJECT_ROOT / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY", default="")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "apps.common.admin_config.AutoBuyAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.cars.apps.CarsConfig",
    "apps.favorites.apps.FavoritesConfig",
    "apps.moderation.apps.ModerationConfig",
    "apps.admin_api.apps.AdminApiConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.dealers.apps.DealersConfig",
    "apps.subscriptions.apps.SubscriptionsConfig",
    "apps.stats.apps.StatsConfig",
    "apps.ads.apps.AdsConfig",
    "apps.alerts.apps.AlertsConfig",
]

MIDDLEWARE = [
    "apps.common.middleware.ClientIPMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_ENGINE = env(
    "DB_ENGINE",
    default="django.db.backends.postgresql",
)
if env("DATABASE_URL", default=""):
    # Render: DATABASE_URL=postgres://user:pass@host:5432/db
    DATABASES = {"default": env.db_url("DATABASE_URL")}
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    DB_ENGINE = DATABASES["default"]["ENGINE"]
elif DB_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": env("DB_NAME", default="autobuy"),
            "USER": env("DB_USER", default="autobuy"),
            "PASSWORD": env("DB_PASSWORD", default=""),
            "HOST": env("DB_HOST", default="localhost"),
            "PORT": env("DB_PORT", default="5432"),
            "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": 5},
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "5/minute",
        "auth_account": "20/hour",
        "auth_2fa": "10/minute",
        "auth_refresh": "30/minute",
        "contacts": "60/hour",
        "rates": "120/hour",
        "reviews": "5/day",
        "ads": "300/hour",
        "ad_events": "600/hour",
        "assistant": "40/hour",
        "alerts": "30/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "CHECK_REVOKE_TOKEN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Заголовок с настоящим IP посетителя от доверенного прокси (см. ClientIPMiddleware).
# Пусто — берётся IP соединения. В production: CF-Connecting-IP (Cloudflare перед Render).
CLIENT_IP_HEADER = env("CLIENT_IP_HEADER", default="")

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[],
)

AUTH_COOKIE_NAME = "autobuy_refresh"
AUTH_COOKIE_PATH = "/api/auth/"
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=not DEBUG)
AUTH_COOKIE_SAMESITE = env(
    "AUTH_COOKIE_SAMESITE",
    default="Lax",
)

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
# Brevo HTTP API: если задан ключ — письма идут через API (Render блокирует SMTP на free)
BREVO_API_KEY = env("BREVO_API_KEY", default="")
if BREVO_API_KEY:
    EMAIL_BACKEND = "apps.common.email_backends.BrevoEmailBackend"
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="no-reply@autobuy.local",
)
PASSWORD_RESET_URL = env("PASSWORD_RESET_URL", default="")

# Payments
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="mock")
FRONTEND_URL = env("FRONTEND_URL", default="https://autobuy-kg.vercel.app")
FINIK_MERCHANT_ID = env("FINIK_MERCHANT_ID", default="")
FINIK_SECRET_KEY = env("FINIK_SECRET_KEY", default="")
FINIK_API_URL = env("FINIK_API_URL", default="https://api.finik.kg/v1")

# Уведомления о тарифах: Telegram-бот пишет администратору площадки
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_ADMIN_CHAT_ID = env("TELEGRAM_ADMIN_CHAT_ID", default="")
# 2FA для администраторов: код входа приходит в Telegram.
# Отдельный бот и чат для кодов; если не заданы — берутся TELEGRAM_BOT_TOKEN / TELEGRAM_ADMIN_CHAT_ID.
TELEGRAM_BOT_ADMIN_TOKEN = env("TELEGRAM_BOT_ADMIN_TOKEN", default="")
TELEGRAM_ADMIN_2FA_CHAT_ID = env("TELEGRAM_ADMIN_2FA_CHAT_ID", default="")
# Аварийно отключить (например, Telegram недоступен): ADMIN_2FA_ENABLED=false
ADMIN_2FA_ENABLED = env.bool("ADMIN_2FA_ENABLED", default=True)
# Секрет для ежедневного запуска напоминаний по HTTP (GitHub Actions / внешний cron)
CRON_SECRET = env("CRON_SECRET", default="")

# Бот уведомлений покупателям (сохранённые поиски, снижение цен). Отдельный от бота кодов входа.
TELEGRAM_ALERTS_BOT_TOKEN = env("TELEGRAM_BOT_USER_TOKEN", default="")
# Имя бота (без @); если не задано — узнаём у Telegram через getMe
TELEGRAM_ALERTS_BOT_USERNAME = env("TELEGRAM_BOT_USER_USERNAME", default="")
# Необязательно: адрес вебхука, если автоопределение по запросу не подходит
TELEGRAM_ALERTS_WEBHOOK_URL = env("TELEGRAM_ALERTS_WEBHOOK_URL", default="")

DATA_UPLOAD_MAX_MEMORY_SIZE = 30 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# ИИ-помощник (Gemini). Пустой ключ — чат отвечает «временно недоступен».
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-2.5-flash")
# Запасные модели, если основная перегружена (через запятую)
GEMINI_FALLBACK_MODELS = env.list("GEMINI_FALLBACK_MODELS", default=["gemini-flash-latest", "gemini-flash-lite-latest"])
