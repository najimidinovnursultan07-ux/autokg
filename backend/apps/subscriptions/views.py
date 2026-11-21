import csv
import hmac

from django.conf import settings
from django.db import transaction

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cars.models import Car
from apps.dealers.models import Dealer
from apps.dealers.permissions import IsAdminRole, IsDealerRole

from .models import Plan, PlanRequest, Subscription
from .notifications import notify_new_request, send_subscription_reminders
from .serializers import (
    ActivateSubscriptionSerializer,
    AdminPlanRequestSerializer,
    AdminSubscriptionSerializer,
    PlanRequestSerializer,
    PlanSerializer,
    PromoteSerializer,
    SubscriptionSerializer,
)
from .services import (
    activate_subscription,
    current_subscription,
    deactivate_subscription,
    usage,
    use_promotion,
)


# ── Публичные ──────────────────────────────────────────────────────────────

class PlanListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PlanSerializer(Plan.objects.filter(is_active=True), many=True).data)


# ── Кабинет салона ─────────────────────────────────────────────────────────

class MySubscriptionView(APIView):
    """Текущий тариф, остаток лимитов и бонусов, последние заявки."""

    permission_classes = [IsDealerRole]

    def get(self, request):
        dealer = request.user.dealer
        subscription = current_subscription(dealer)
        upcoming = (
            Subscription.objects.filter(dealer=dealer, starts_at__gt=timezone.now())
            .select_related("plan").order_by("starts_at")
        )
        requests = PlanRequest.objects.filter(dealer=dealer).select_related("plan")[:5]
        return Response({
            "subscription": SubscriptionSerializer(subscription).data if subscription else None,
            "upcoming": SubscriptionSerializer(upcoming, many=True).data,
            "usage": usage(dealer, subscription),
            "requests": PlanRequestSerializer(requests, many=True).data,
        })


class PlanRequestCreateView(APIView):
    """Заявка на подключение/продление. Повторная заявка заменяет необработанную."""

    permission_classes = [IsDealerRole]

    def post(self, request):
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dealer = request.user.dealer
        existing = PlanRequest.objects.filter(dealer=dealer, status=PlanRequest.Status.NEW).first()
        if existing:
            for key, value in serializer.validated_data.items():
                setattr(existing, key, value)
            existing.created_by = request.user
            existing.save()
            obj, code = existing, status.HTTP_200_OK
        else:
            obj, code = serializer.save(dealer=dealer, created_by=request.user), status.HTTP_201_CREATED
        transaction.on_commit(lambda: notify_new_request(obj))
        data = PlanRequestSerializer(obj).data
        data["detail"] = "Заявка отправлена. Менеджер свяжется с вами для оплаты."
        return Response(data, status=code)


class PromoteView(APIView):
    """Продвижение объявления за счёт бонусов тарифа (без оплаты на сайте)."""

    permission_classes = [IsDealerRole]

    def post(self, request):
        serializer = PromoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dealer = request.user.dealer
        car = get_object_or_404(Car, pk=serializer.validated_data["car_id"], dealer=dealer)
        promotion = use_promotion(dealer, car, serializer.validated_data["promotion_type"])
        return Response(
            {
                "detail": "Продвижение включено на 7 дней.",
                "promotion_type": promotion.promotion_type,
                "expires_at": promotion.expires_at,
                "usage": usage(dealer),
            },
            status=status.HTTP_201_CREATED,
        )


class StatsExportView(APIView):
    """Выгрузка статистики объявлений в CSV (открывается в Excel). Только тариф с экспортом."""

    permission_classes = [IsDealerRole]

    def get(self, request):
        dealer = request.user.dealer
        subscription = current_subscription(dealer)
        if not subscription or subscription.plan.stats_level != Plan.StatsLevel.EXPORT:
            return Response(
                {"detail": "Выгрузка статистики доступна на тарифе «Премиум»."},
                status=status.HTTP_403_FORBIDDEN,
            )
        cars = (
            Car.objects.filter(dealer=dealer)
            .select_related("model", "model__brand", "city")
            .order_by("-created_at")
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"stats-{dealer.storage_folder}-{timezone.localdate():%Y-%m-%d}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write("﻿")  # BOM — чтобы Excel правильно открыл кириллицу
        writer = csv.writer(response, delimiter=";")
        writer.writerow([
            "Автомобиль", "Год", "Цена", "Валюта", "Город", "Статус",
            "Просмотры", "Открыли номер", "WhatsApp", "Опубликовано",
        ])
        for car in cars:
            writer.writerow([
                f"{car.model.brand.name} {car.model.name}", car.year, car.price, car.currency,
                car.city.name, car.get_status_display(), car.views_count, car.phone_views,
                car.whatsapp_clicks,
                timezone.localtime(car.published_at).strftime("%d.%m.%Y") if car.published_at else "",
            ])
        return response


# ── Админ ──────────────────────────────────────────────────────────────────

class AdminPlanViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Тарифы: просмотр и изменение цен/лимитов без правки кода."""

    permission_classes = [IsAdminRole]
    serializer_class = PlanSerializer
    queryset = Plan.objects.all()
    pagination_class = None
    http_method_names = ("get", "patch", "head", "options")


class AdminSubscriptionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AdminSubscriptionSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Subscription.objects.select_related("dealer", "plan", "created_by")
        dealer = self.request.query_params.get("dealer")
        if dealer:
            qs = qs.filter(dealer_id=dealer)
        return qs[:200]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Все салоны с текущим тарифом и датой окончания."""
        now = timezone.now()
        dealers = Dealer.objects.order_by("name")
        current = {}
        for sub in (
            Subscription.objects.filter(expires_at__gt=now)
            .select_related("plan").order_by("starts_at")
        ):
            if sub.starts_at <= now:
                current[sub.dealer_id] = sub
        last_expires = {}
        for sub in Subscription.objects.order_by("expires_at").only("dealer_id", "expires_at"):
            last_expires[sub.dealer_id] = sub.expires_at
        new_requests = set(
            PlanRequest.objects.filter(status=PlanRequest.Status.NEW).values_list("dealer_id", flat=True)
        )
        rows = []
        for dealer in dealers:
            sub = current.get(dealer.pk)
            rows.append({
                "dealer": dealer.pk,
                "dealer_name": dealer.name,
                "dealer_slug": dealer.slug,
                "dealer_is_active": dealer.is_active,
                "subscription": SubscriptionSerializer(sub).data if sub else None,
                "paid_until": last_expires.get(dealer.pk),
                "has_new_request": dealer.pk in new_requests,
            })
        return Response(rows)

    def create(self, request):
        serializer = ActivateSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sub = activate_subscription(
            data["dealer"], data["plan"], data["months"],
            by=request.user,
            amount=data.get("amount"),
            payment_method=data.get("payment_method", ""),
            note=data.get("note", ""),
        )
        request_id = data.get("request_id")
        if request_id:
            PlanRequest.objects.filter(pk=request_id, dealer=data["dealer"]).update(
                status=PlanRequest.Status.DONE, processed_at=timezone.now()
            )
        return Response(AdminSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def deactivate(self, request):
        dealer = get_object_or_404(Dealer, pk=request.data.get("dealer"))
        deactivate_subscription(dealer)
        return Response({"detail": f"Тариф салона «{dealer.name}» отключён, объявления скрыты."})


class AdminPlanRequestViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    permission_classes = [IsAdminRole]
    serializer_class = AdminPlanRequestSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_queryset(self):
        qs = PlanRequest.objects.select_related("dealer", "plan", "created_by")
        status_value = self.request.query_params.get("status")
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        processed_at = None if new_status == PlanRequest.Status.NEW else timezone.now()
        serializer.save(processed_at=processed_at)


# ── Ежедневные напоминания (внешний cron) ──────────────────────────────────

class SubscriptionRemindersView(APIView):
    """
    POST с заголовком X-Cron-Secret = CRON_SECRET. Без настроенного секрета — 404.
    То же самое делает команда: python manage.py send_subscription_reminders
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = settings.CRON_SECRET
        given = request.headers.get("X-Cron-Secret", "")
        if not secret:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not hmac.compare_digest(given.encode(), secret.encode()):
            return Response({"detail": "Неверный секрет."}, status=status.HTTP_403_FORBIDDEN)
        from apps.stats.services import purge_old_stats

        result = send_subscription_reminders()
        result["stats_removed"] = purge_old_stats()  # хранение статистики — 12 месяцев
        return Response(result)
