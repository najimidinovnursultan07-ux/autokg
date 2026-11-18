from decimal import Decimal
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q


class CarStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PENDING = "pending", "На модерации"
    PUBLISHED = "published", "Опубликовано"
    REJECTED = "rejected", "Отклонено"
    INACTIVE = "inactive", "Снято с публикации"
    SOLD = "sold", "Продано"
    REMOVED = "removed", "Удалено"


class CarEngineType(models.TextChoices):
    PETROL = "petrol", "Бензин"
    DIESEL = "diesel", "Дизель"
    HYBRID = "hybrid", "Гибрид"
    ELECTRIC = "electric", "Электро"
    LPG = "lpg", "Газ"
    OTHER = "other", "Другое"


class CarTransmission(models.TextChoices):
    MANUAL = "manual", "Механическая"
    AUTOMATIC = "automatic", "Автоматическая"
    CVT = "cvt", "Вариатор"
    ROBOTIC = "robotic", "Робот"


class CarDriveType(models.TextChoices):
    FWD = "fwd", "Передний"
    RWD = "rwd", "Задний"
    AWD = "awd", "Полный"


class CarBodyType(models.TextChoices):
    SEDAN = "sedan", "Седан"
    HATCHBACK = "hatchback", "Хэтчбек"
    SUV = "suv", "Внедорожник"
    WAGON = "wagon", "Универсал"
    COUPE = "coupe", "Купе"
    MINIVAN = "minivan", "Минивэн"
    PICKUP = "pickup", "Пикап"
    OTHER = "other", "Другое"


class CarCondition(models.TextChoices):
    NEW = "new", "Новый"
    USED = "used", "С пробегом"
    DAMAGED = "damaged", "Требует ремонта"


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Model(models.Model):
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="models",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("brand__name", "name")
        indexes = [
            models.Index(fields=("brand", "is_active")),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("brand", "name"),
                name="unique_model_per_brand",
            ),
            models.UniqueConstraint(
                fields=("brand", "slug"),
                name="unique_model_slug_per_brand",
            ),
        ]

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class Car(models.Model):
    Status = CarStatus
    EngineType = CarEngineType
    Transmission = CarTransmission
    DriveType = CarDriveType
    BodyType = CarBodyType
    Condition = CarCondition

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cars",
    )
    model = models.ForeignKey(
        Model,
        on_delete=models.PROTECT,
        related_name="cars",
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="cars",
    )
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1886), MaxValueValidator(2100)]
    )
    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    mileage = models.PositiveIntegerField(default=0)
    engine_volume = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.1"))],
    )
    engine_type = models.CharField(max_length=16, choices=CarEngineType.choices)
    transmission = models.CharField(max_length=16, choices=CarTransmission.choices)
    drive_type = models.CharField(max_length=8, choices=CarDriveType.choices)
    body_type = models.CharField(max_length=16, choices=CarBodyType.choices)
    condition = models.CharField(max_length=16, choices=CarCondition.choices)
    description = models.TextField(max_length=10_000)
    contact_phone = models.CharField(
        max_length=16,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9]{7,15}$",
                message="Введите телефон в международном формате.",
            )
        ],
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    views_count = models.PositiveIntegerField(default=0, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=("status", "price")),
            models.Index(fields=("status", "year")),
            models.Index(fields=("model", "status")),
            models.Index(fields=("city", "status")),
            models.Index(fields=("status", "mileage")),
            models.Index(fields=("status", "engine_type")),
            models.Index(fields=("status", "transmission")),
            models.Index(fields=("status", "body_type")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(year__gte=1886, year__lte=2100),
                name="car_year_in_supported_range",
            ),
            models.CheckConstraint(
                condition=Q(price__gte=0),
                name="car_price_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(mileage__gte=0),
                name="car_mileage_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(engine_volume__isnull=True) | Q(engine_volume__gt=0),
                name="car_engine_volume_positive_or_null",
            ),
            models.CheckConstraint(
                condition=Q(status__in=CarStatus.values),
                name="car_status_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(engine_type__in=CarEngineType.values),
                name="car_engine_type_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(transmission__in=CarTransmission.values),
                name="car_transmission_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(drive_type__in=CarDriveType.values),
                name="car_drive_type_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(body_type__in=CarBodyType.values),
                name="car_body_type_is_valid",
            ),
            models.CheckConstraint(
                condition=Q(condition__in=CarCondition.values),
                name="car_condition_is_valid",
            ),
        ]

    @property
    def brand(self):
        return self.model.brand

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})"


def car_image_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
        extension = ".jpg"
    return f"cars/{instance.car_id}/{uuid.uuid4().hex}{extension}"


class CarImage(models.Model):
    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=car_image_upload_to)
    position = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("car", "position"),
                name="unique_car_image_position",
            ),
            models.UniqueConstraint(
                fields=("car",),
                condition=Q(is_cover=True),
                name="unique_cover_image_per_car",
            ),
        ]

    def clean(self):
        super().clean()
        if self.is_cover and self.car_id:
            has_another_cover = CarImage.objects.filter(
                car_id=self.car_id,
                is_cover=True,
            ).exclude(pk=self.pk).exists()
            if has_another_cover:
                raise ValidationError(
                    {"is_cover": "У объявления может быть только одна обложка."}
                )

    def __str__(self):
        return f"Image for {self.car_id}"
