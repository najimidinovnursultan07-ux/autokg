import hashlib
import hmac
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cars.models import Car
from .models import (
    SERVICE_DURATIONS,
    SERVICE_PRICES,
    Payment,
    PaymentStatus,
    Promotion,
    ServiceType,
)
from .serializers import (
    CreatePaymentSerializer,
    PaymentSerializer,
    ServicePriceSerializer,
)


class ServicePricesView(APIView):
    """Возвращает актуальные цены услуг с бэкенда."""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import SERVICE_PRICES, SERVICE_DURATIONS
        data = []
        for st in ServiceType.values:
            data.append({
                "service_type": st,
                "label": dict(ServiceType.choices).get(st, st),
                "amount": str(SERVICE_PRICES.get(st, "0.00")),
                "duration_days": SERVICE_DURATIONS.get(st, 7),
                "currency": "KGS",
            })
        return Response(data)


class CreatePaymentView(APIView):
    """Создаёт платёж и возвращает ссылку для оплаты."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        car_id = serializer.validated_data["car_id"]
        service_type = serializer.validated_data["service_type"]

        car = get_object_or_404(Car, pk=car_id)

        # Продвигать объявление может только менеджер его салона
        if not request.user.dealer_id or car.dealer_id != request.user.dealer_id:
            return Response(
                {"detail": "Вы не являетесь владельцем этого объявления."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Цена берётся с бэкенда — фронтенд не может изменить сумму
        amount = SERVICE_PRICES[service_type]

        # Проверяем, нет ли уже активной услуги этого типа
        already_active = Promotion.objects.filter(
            car=car,
            promotion_type=service_type,
            is_active=True,
            expires_at__gt=timezone.now(),
        ).exists()
        if already_active:
            return Response(
                {"detail": "У этого объявления уже есть активная услуга данного типа."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            payment = Payment.objects.create(
                user=request.user,
                car=car,
                service_type=service_type,
                amount=amount,
                currency="KGS",
                provider=getattr(settings, "PAYMENT_PROVIDER", "mock"),
            )

        # Получаем платёжную ссылку от провайдера
        payment_url = self._get_payment_url(payment)

        return Response(
            {
                "payment_id": str(payment.id),
                "payment_url": payment_url,
                "amount": str(amount),
                "currency": "KGS",
                "service_type": service_type,
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_payment_url(self, payment):
        provider = getattr(settings, "PAYMENT_PROVIDER", "mock")
        if provider == "mock":
            # Тестовый режим — возвращаем внутренний URL
            base = getattr(settings, "FRONTEND_URL", "https://autobuy-kg.vercel.app")
            return f"{base}/payment/mock?payment_id={payment.id}"
        # Finik — будет реализовано после получения реальных ключей
        return ""


class MockPaymentView(APIView):
    """
    Тестовый провайдер — подтверждает или отменяет платёж без реальных денег.
    Только в режиме PAYMENT_PROVIDER=mock.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if getattr(settings, "PAYMENT_PROVIDER", "mock") != "mock":
            return Response(
                {"detail": "Mock-платежи отключены в продакшене."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payment_id = request.data.get("payment_id")
        action = request.data.get("action", "pay")  # "pay" или "cancel"

        payment = get_object_or_404(
            Payment,
            pk=payment_id,
            user=request.user,
            status=PaymentStatus.PENDING,
        )

        with transaction.atomic():
            if action == "cancel":
                payment.status = PaymentStatus.CANCELLED
                payment.save(update_fields=("status", "updated_at"))
                return Response({"detail": "Платёж отменён.", "status": "cancelled"})

            # Успешная оплата
            payment.status = PaymentStatus.PAID
            payment.paid_at = timezone.now()
            payment.transaction_id = f"mock_{uuid.uuid4().hex[:12]}"
            payment.save(update_fields=("status", "paid_at", "transaction_id", "updated_at"))

            # Активируем услугу
            duration = SERVICE_DURATIONS[payment.service_type]
            now = timezone.now()
            Promotion.objects.create(
                car=payment.car,
                promotion_type=payment.service_type,
                payment=payment,
                starts_at=now,
                expires_at=now + timedelta(days=duration),
                is_active=True,
            )

        return Response({
            "detail": "Оплата прошла успешно.",
            "status": "paid",
            "transaction_id": payment.transaction_id,
        })


class PaymentHistoryView(APIView):
    """История платежей текущего пользователя."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = (
            Payment.objects
            .filter(user=request.user)
            .select_related("car", "car__model", "car__model__brand", "promotion")
            .order_by("-created_at")
        )
        # Автоматически деактивируем просроченные услуги
        for p in payments:
            if hasattr(p, "promotion") and p.promotion:
                p.promotion.deactivate_if_expired()

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


class CarPromotionsView(APIView):
    """Активные промоции конкретного автомобиля."""
    permission_classes = [AllowAny]

    def get(self, request, car_id):
        # Деактивируем просроченные
        Promotion.objects.filter(
            car_id=car_id,
            is_active=True,
            expires_at__lte=timezone.now(),
        ).update(is_active=False)

        promotions = Promotion.objects.filter(
            car_id=car_id,
            is_active=True,
        )
        from .serializers import PromotionSerializer
        return Response(PromotionSerializer(promotions, many=True).data)


class WebhookView(APIView):
    """
    Webhook endpoint для реального платёжного провайдера (Finik).
    Сейчас возвращает 501 — реализуется после получения реальных ключей.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {"detail": "Webhook Finik — ожидает реальных API-ключей."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
