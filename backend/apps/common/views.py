import logging

from django.db import OperationalError, connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .rates import get_rates


logger = logging.getLogger(__name__)


class ApiRootView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "AutoBuy API",
            "version": "1.0",
            "status": "ok",
            "docs": {
                "health": "/api/health/",
                "auth": "/api/auth/",
                "cars": "/api/cars/",
                "favorites": "/api/favorites/",
                "admin": "/api/admin/",
            },
        })


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connection.ensure_connection()
        except OperationalError:
            logger.exception("Database readiness check failed")
            return Response(
                {"status": "unavailable", "service": "database"},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ready", "database": "ok"})


class ExchangeRatesView(APIView):
    """Курс НБКР: сколько сомов за 1 USD/EUR/RUB/KZT/CNY."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "rates"

    def get(self, request):
        data = get_rates()
        if not data:
            return Response({"detail": "Курс временно недоступен."}, status=HTTP_503_SERVICE_UNAVAILABLE)
        response = Response(data)
        response["Cache-Control"] = "public, max-age=3600"
        return response


class AssistantChatView(APIView):
    """
    POST /api/assistant/chat/ — ИИ-помощник (Gemini).
    Тело: {"messages": [{"role": "user"|"model", "text": "..."}]} — история диалога,
    последнее сообщение от пользователя. Ответ: {"reply": "...", "cars": [...], "ads": [...]}.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "assistant"

    MAX_MESSAGES = 16
    MAX_TEXT = 1000

    def post(self, request):
        from .assistant import AssistantUnavailable, car_summary, chat
        from .media import cloudinary_variant, file_url

        messages = request.data.get("messages") if isinstance(request.data, dict) else None
        if not isinstance(messages, list) or not messages:
            return Response({"detail": "Напишите сообщение."}, status=400)
        history = []
        for item in messages[-self.MAX_MESSAGES:]:
            if not isinstance(item, dict):
                return Response({"detail": "Неверный формат сообщений."}, status=400)
            role = item.get("role")
            text = item.get("text")
            if role not in ("user", "model") or not isinstance(text, str) or not text.strip():
                return Response({"detail": "Неверный формат сообщений."}, status=400)
            history.append({"role": role, "text": text.strip()[: self.MAX_TEXT]})
        while history and history[0]["role"] != "user":
            history.pop(0)  # Gemini ждёт, что диалог начинается с пользователя
        if not history or history[-1]["role"] != "user":
            return Response({"detail": "Напишите сообщение."}, status=400)

        try:
            reply, cars, ads = chat(history)
        except AssistantUnavailable:
            return Response(
                {"detail": "Помощник временно недоступен. Попробуйте позже или напишите нам в WhatsApp."},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )

        cards = []
        for car in cars:
            summary = car_summary(car)
            image = summary.pop("image")
            summary["image"] = cloudinary_variant(
                file_url(image.image, request), "f_auto,q_auto,c_limit,w_400"
            ) if image else None
            cards.append(summary)
        from apps.ads.serializers import PublicAdSerializer

        ad_cards = PublicAdSerializer(ads, many=True, context={"request": request}).data
        if not reply:
            reply = "Вот что нашлось:" if cards or ad_cards else "Не получилось ответить. Переформулируйте вопрос, пожалуйста."
        return Response({"reply": reply, "cars": cards, "ads": ad_cards})
