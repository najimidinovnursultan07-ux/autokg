"""
Тарифы автосалонов. Оплата на сайте не принимается: салон оставляет заявку,
платит напрямую, администратор включает тариф вручную (Subscription).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

TRIAL_PLAN_CODE = "business"
TRIAL_DAYS = 14
PROMOTION_DAYS = 7
PERIOD_MONTHS = (1, 3, 12)


class Plan(models.Model):
    class StatsLevel(models.TextChoices):
        BASIC = "basic", "Только просмотры"
        FULL = "full", "Просмотры, звонки, WhatsApp"
        EXPORT = "export", "Полная + выгрузка в Excel"

    code = models.SlugField("Код", max_length=32, unique=True)
    name = models.CharField("Название", max_length=60)
    price_month = models.DecimalField("Цена за месяц", max_digits=10, decimal_places=2)
    price_3_months = models.DecimalField("Цена за 3 месяца", max_digits=10, decimal_places=2)
    price_12_months = models.DecimalField("Цена за год", max_digits=10, decimal_places=2)
    max_active_cars = models.PositiveIntegerField("Активных объявлений одновременно")
    top_per_month = models.PositiveIntegerField("ТОП-поднятий в месяц", default=0)
    highlight_per_month = models.PositiveIntegerField("Выделений в месяц", default=0)
    # null — без ограничений
    urgent_per_month = models.PositiveIntegerField(
        "«Срочно» в месяц", default=0, null=True, blank=True,
        help_text="Пусто — без ограничений.",
    )
    has_badge = models.BooleanField("Бейдж «Проверенный дилер»", default=False)
    stats_level = models.CharField(
        "Статистика", max_length=16, choices=StatsLevel.choices, default=StatsLevel.BASIC
    )
    has_excel_import = models.BooleanField("Загрузка из Excel", default=False)
    list_priority = models.PositiveSmallIntegerField(
        "Приоритет в списке дилеров", default=0, help_text="Чем больше, тем выше."
    )
    featured_on_home = models.BooleanField("Блок на главной", default=False)
    priority_support = models.BooleanField("Приоритетная поддержка", default=False)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_active = models.BooleanField("Доступен для подключения", default=True)

    class Meta:
        ordering = ("sort_order", "price_month")
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"

    def __str__(self):
        return self.name

    def price_for(self, months):
        return {1: self.price_month, 3: self.price_3_months, 12: self.price_12_months}.get(months)

    def quota(self, promotion_type):
        """Сколько продвижений данного типа в месяц; None — без ограничений."""
        return {
            "top": self.top_per_month,
            "highlight": self.highlight_per_month,
            "urgent": self.urgent_per_month,
        }[promotion_type]


class SubscriptionQuerySet(models.QuerySet):
    def current(self, at=None):
        at = at or timezone.now()
        return self.filter(starts_at__lte=at, expires_at__gt=at)


class Subscription(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Наличные"
        TRANSFER = "transfer", "Перевод"
        INVOICE = "invoice", "Счёт"
        OTHER = "other", "Другое"

    dealer = models.ForeignKey(
        "dealers.Dealer", on_delete=models.CASCADE, related_name="subscriptions", verbose_name="Автосалон"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions", verbose_name="Тариф")
    starts_at = models.DateTimeField("Начало", db_index=True)
    expires_at = models.DateTimeField("Окончание", db_index=True)
    is_trial = models.BooleanField("Пробный период", default=False)
    months = models.PositiveSmallIntegerField("Срок, мес.", null=True, blank=True)
    # Учёт оплаты вне сайта — только для администратора
    amount = models.DecimalField("Получено, сом", max_digits=10, decimal_places=2, null=True, blank=True)
    payment_method = models.CharField(
        "Способ оплаты", max_length=16, choices=PaymentMethod.choices, blank=True
    )
    note = models.CharField("Комментарий", max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="Кто включил",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # Какие напоминания уже отправлены: "3", "1", "expired"
    reminders_sent = models.JSONField("Отправленные напоминания", default=list, blank=True)

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        ordering = ("-starts_at",)
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        indexes = [models.Index(fields=("dealer", "starts_at", "expires_at"))]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("starts_at")),
                name="subscription_expires_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.dealer} — {self.plan} до {self.expires_at:%d.%m.%Y}"


class PlanRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        DONE = "done", "Обработана"
        REJECTED = "rejected", "Отклонена"

    dealer = models.ForeignKey(
        "dealers.Dealer", on_delete=models.CASCADE, related_name="plan_requests", verbose_name="Автосалон"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="requests", verbose_name="Тариф")
    months = models.PositiveSmallIntegerField("Срок, мес.", default=1)
    comment = models.CharField("Комментарий", max_length=500, blank=True)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.NEW, db_index=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Заявка на тариф"
        verbose_name_plural = "Заявки на тарифы"

    def __str__(self):
        return f"{self.dealer} → {self.plan} ({self.months} мес.)"
