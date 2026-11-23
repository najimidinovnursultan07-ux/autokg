"""
Рекламные баннеры партнёров (банки, страховые, автосервисы и т.д.).

Админ загружает баннер, выбирает место показа и период. Сайт показывает
активные баннеры, считает показы и клики (общие счётчики + по дням для
отчёта рекламодателю).
"""
import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, URLValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


def ad_image_upload_to(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"ads/{uuid.uuid4().hex}{ext}"


class AdPlacement(models.TextChoices):
    HOME_TOP = "home_top", "Главная — сверху"
    HOME_MIDDLE = "home_middle", "Главная — между блоками"
    CATALOG_FEED = "catalog_feed", "Каталог — в списке объявлений"
    CAR_DETAIL = "car_detail", "Страница авто — рядом с контактами"


# Сколько баннеров одновременно крутится в слайдере одного места показа
MAX_BANNERS_PER_PLACEMENT = 3
PLACEMENT_FULL_MESSAGE = (
    f"На этом месте в эти даты уже {MAX_BANNERS_PER_PLACEMENT} включённых баннера — "
    "выключите один из них или выберите другие даты."
)


class AdBannerQuerySet(models.QuerySet):
    def overlapping(self, placement, starts_on, ends_on, exclude_pk=None):
        """Включённые баннеры места placement, чей период пересекается с [starts_on, ends_on]."""
        today = timezone.localdate()
        qs = self.filter(placement=placement, is_active=True).filter(
            Q(ends_on__isnull=True) | Q(ends_on__gte=max(starts_on or today, today))
        )
        if ends_on:
            qs = qs.filter(Q(starts_on__isnull=True) | Q(starts_on__lte=ends_on))
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs

    def live(self, today=None):
        """Включённые баннеры, у которых сегодняшний день попадает в период показа."""
        today = today or timezone.localdate()
        return self.filter(
            Q(starts_on__isnull=True) | Q(starts_on__lte=today),
            Q(ends_on__isnull=True) | Q(ends_on__gte=today),
            is_active=True,
        )


class AdBanner(models.Model):
    Placement = AdPlacement

    title = models.CharField("Название (для себя и alt)", max_length=120)
    advertiser = models.CharField("Рекламодатель", max_length=120)
    advertiser_contact = models.CharField("Контакт рекламодателя", max_length=120, blank=True)
    placement = models.CharField("Место показа", max_length=20, choices=AdPlacement.choices, db_index=True)
    image = models.ImageField("Картинка", upload_to=ad_image_upload_to)
    mobile_image = models.ImageField(
        "Картинка для телефона", upload_to=ad_image_upload_to, blank=True, null=True
    )
    link_url = models.URLField(
        "Ссылка", max_length=500, validators=[URLValidator(schemes=["http", "https"])]
    )
    starts_on = models.DateField("Показывать с", null=True, blank=True)
    ends_on = models.DateField("Показывать по", null=True, blank=True)
    is_active = models.BooleanField("Включён", default=True)
    priority = models.PositiveSmallIntegerField(
        "Приоритет",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="1–10: чем больше, тем чаще показывается среди баннеров того же места.",
    )
    price = models.DecimalField(
        "Сумма по договору, сом", max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    is_paid = models.BooleanField("Оплачено", default=False)
    impressions = models.PositiveIntegerField("Показы", default=0)
    clicks = models.PositiveIntegerField("Клики", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AdBannerQuerySet.as_manager()

    class Meta:
        verbose_name = "Рекламный баннер"
        verbose_name_plural = "Рекламные баннеры"
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=Q(starts_on__isnull=True) | Q(ends_on__isnull=True) | Q(ends_on__gte=F("starts_on")),
                name="ad_banner_period_valid",
            ),
        ]

    def __str__(self):
        return f"{self.advertiser} — {self.title}"

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValidationError({"ends_on": "Дата окончания раньше даты начала."})
        if self.is_active and self.placement and (
            AdBanner.objects.overlapping(self.placement, self.starts_on, self.ends_on, exclude_pk=self.pk).count()
            >= MAX_BANNERS_PER_PLACEMENT
        ):
            raise ValidationError({"placement": PLACEMENT_FULL_MESSAGE})

    @property
    def is_live(self):
        today = timezone.localdate()
        return (
            self.is_active
            and (self.starts_on is None or self.starts_on <= today)
            and (self.ends_on is None or self.ends_on >= today)
        )


class AdPlacementPrice(models.Model):
    """Прайс на рекламу: цена места показа за 7 и за 30 дней (меняет админ)."""

    placement = models.CharField("Место показа", max_length=20, choices=AdPlacement.choices, unique=True)
    price_week = models.DecimalField(
        "Цена за 7 дней, сом", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    price_month = models.DecimalField(
        "Цена за 30 дней, сом", max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Цена рекламного места"
        verbose_name_plural = "Цены на рекламу"

    def __str__(self):
        return f"{self.get_placement_display()}: {self.price_week} / {self.price_month} сом"

    @classmethod
    def all_placements(cls):
        """Строки для всех мест показа (недостающие создаются с нулевой ценой)."""
        existing = {p.placement: p for p in cls.objects.all()}
        for value in AdPlacement.values:
            if value not in existing:
                existing[value] = cls.objects.create(placement=value)
        return [existing[value] for value in AdPlacement.values]


class AdDailyStat(models.Model):
    banner = models.ForeignKey(AdBanner, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField("День")
    impressions = models.PositiveIntegerField("Показы", default=0)
    clicks = models.PositiveIntegerField("Клики", default=0)

    class Meta:
        verbose_name = "Статистика баннера за день"
        verbose_name_plural = "Статистика баннеров по дням"
        ordering = ("date",)
        constraints = [models.UniqueConstraint(fields=("banner", "date"), name="ad_daily_stat_unique")]
