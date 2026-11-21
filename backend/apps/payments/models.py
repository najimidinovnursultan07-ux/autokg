import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class ServiceType(models.TextChoices):
    TOP = "top", "ТОП-объявление"
    HIGHLIGHT = "highlight", "Выделить объявление"
    URGENT = "urgent", "Срочное объявление"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Ожидает оплаты"
    PAID = "paid", "Успешно оплачено"
    FAILED = "failed", "Ошибка оплаты"
    CANCELLED = "cancelled", "Отменено"
    REFUNDED = "refunded", "Возврат средств"


# Цены хранятся на бэкенде — фронтенд не может изменить сумму
SERVICE_PRICES = {
    ServiceType.TOP: Decimal("500.00"),
    ServiceType.HIGHLIGHT: Decimal("200.00"),
    ServiceType.URGENT: Decimal("150.00"),
}

# Длительность услуги в днях
SERVICE_DURATIONS = {
    ServiceType.TOP: 7,
    ServiceType.HIGHLIGHT: 7,
    ServiceType.URGENT: 7,
}


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    # SET_NULL: при удалении машины история платежей сохраняется
    car = models.ForeignKey(
        "cars.Car",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    service_type = models.CharField(max_length=16, choices=ServiceType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default="KGS")
    provider = models.CharField(max_length=32, default="mock")
    transaction_id = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    provider_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.service_type} | {self.user_id} | {self.status}"


class Promotion(models.Model):
    car = models.ForeignKey(
        "cars.Car",
        on_delete=models.CASCADE,
        related_name="promotions",
    )
    promotion_type = models.CharField(max_length=16, choices=ServiceType.choices)
    # Пусто — продвижение из бонусов тарифа (оплата на сайте не принимается)
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="promotion",
        null=True,
        blank=True,
    )
    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("car", "promotion_type", "is_active")),
        ]

    def __str__(self):
        return f"{self.promotion_type} | car={self.car_id} | active={self.is_active}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def deactivate_if_expired(self):
        if self.is_active and self.is_expired:
            self.is_active = False
            self.save(update_fields=("is_active",))
            return True
        return False
