import hmac
import logging

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import telegram
from .models import PriceWatch, SavedSearch
from .services import clean_filters, ensure_title, filters_are_valid, handle_update, run_alerts

logger = logging.getLogger(__name__)

NOT_CONFIGURED = {"detail": "Уведомления в Telegram пока не подключены."}


class SavedSearchInput(serializers.Serializer):
    filters = serializers.DictField(required=False, default=dict)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")


class PriceWatchInput(serializers.Serializer):
    car = serializers.UUIDField()


class PublicAlertView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "alerts"


def ensure_webhook_soon(request):
    """Подключает бота к сайту при первой подписке, не дожидаясь рассылки (проверка раз в час)."""
    if cache.add("alerts-webhook-checked", True, 60 * 60):
        try:
            telegram.ensure_webhook(webhook_url(request))
        except Exception:
            logger.exception("Не удалось настроить вебхук бота уведомлений")


class SavedSearchCreateView(PublicAlertView):
    """Новая подписка на поиск; в ответе — ссылка на бота с токеном."""

    def post(self, request):
        if not telegram.is_configured():
            return Response(NOT_CONFIGURED, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        data = SavedSearchInput(data=request.data)
        data.is_valid(raise_exception=True)
        filters = clean_filters(data.validated_data["filters"])
        if not filters_are_valid(filters):
            return Response({"detail": "Некорректные фильтры поиска."}, status=status.HTTP_400_BAD_REQUEST)
        ensure_webhook_soon(request)
        search = SavedSearch.objects.create(
            filters=filters, title=ensure_title(data.validated_data["title"], filters)
        )
        return Response(
            {"bot_url": telegram.start_link(f"s_{search.token}"), "title": search.title},
            status=status.HTTP_201_CREATED,
        )


class PriceWatchCreateView(PublicAlertView):
    def post(self, request):
        from apps.cars.views import public_cars_queryset

        if not telegram.is_configured():
            return Response(NOT_CONFIGURED, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        data = PriceWatchInput(data=request.data)
        data.is_valid(raise_exception=True)
        car = public_cars_queryset().prefetch_related(None).filter(pk=data.validated_data["car"]).first()
        if car is None:
            return Response({"detail": "Объявление не найдено."}, status=status.HTTP_404_NOT_FOUND)
        ensure_webhook_soon(request)
        watch = PriceWatch.objects.create(car=car, last_price=car.price, currency=car.currency)
        return Response({"bot_url": telegram.start_link(f"w_{watch.token}")}, status=status.HTTP_201_CREATED)


class TelegramWebhookView(APIView):
    """Сюда Telegram присылает сообщения боту. Проверяется секрет из заголовка."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        given = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not telegram.bot_token() or not hmac.compare_digest(given.encode(), telegram.webhook_secret().encode()):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if isinstance(request.data, dict):
            try:
                handle_update(request.data)
            except Exception:
                # Telegram повторяет запрос при ошибке — не зацикливаемся на одном сообщении
                logger.exception("Ошибка обработки сообщения бота уведомлений")
        return Response({"ok": True})


def webhook_url(request):
    url = getattr(settings, "TELEGRAM_ALERTS_WEBHOOK_URL", "") or request.build_absolute_uri(
        reverse("alerts-telegram-webhook")
    )
    if not settings.DEBUG and url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    return url


class AlertsRunView(APIView):
    """Рассылка по расписанию: POST с заголовком X-Cron-Secret = CRON_SECRET."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = settings.CRON_SECRET
        if not secret:
            return Response(status=status.HTTP_404_NOT_FOUND)
        given = request.headers.get("X-Cron-Secret", "")
        if not hmac.compare_digest(given.encode(), secret.encode()):
            return Response({"detail": "Неверный секрет."}, status=status.HTTP_403_FORBIDDEN)
        result = {}
        if telegram.is_configured():
            result["webhook_updated"] = telegram.ensure_webhook(webhook_url(request))
        result.update(run_alerts())
        return Response(result)
