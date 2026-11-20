import re
import uuid
from pathlib import Path

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "ң": "n", "о": "o", "ө": "o", "п": "p", "р": "r", "с": "s",
    "т": "t", "у": "u", "ү": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
    "я": "ya",
})
_SAFE_SLUG = re.compile(r"^[a-z0-9-]+$")


def make_ascii_slug(value):
    """Латинский slug из кириллического названия (для URL и папок Cloudinary)."""
    return slugify(str(value).lower().translate(_TRANSLIT))


def dealer_logo_upload_to(instance, filename):
    ext = Path(filename).suffix.lower()
    return f"dealers/logos/{instance.storage_folder}-{uuid.uuid4().hex}{ext}"


class Dealer(models.Model):
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True, blank=True)
    logo = models.ImageField(
        "Логотип",
        upload_to=dealer_logo_upload_to,
        blank=True,
        null=True,
    )
    description = models.TextField("Описание", blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=20, blank=True)
    address = models.CharField("Адрес", max_length=300, blank=True)
    # Точка на карте 2ГИС (ставится кликом по карте в профиле салона)
    latitude = models.DecimalField(
        "Широта", max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        "Долгота", max_digits=9, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    city = models.ForeignKey(
        "cars.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dealers",
        verbose_name="Город",
    )
    is_active = models.BooleanField("Активен", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Автосалон"
        verbose_name_plural = "Автосалоны"

    @property
    def storage_folder(self):
        """Имя папки в хранилище: slug, если он латинский, иначе dealer-{id}."""
        if self.slug and _SAFE_SLUG.match(self.slug):
            return self.slug
        return f"dealer-{self.pk}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = make_ascii_slug(self.name) or "dealer"
            slug = base
            n = 1
            while Dealer.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DealerReview(models.Model):
    """Отзыв о салоне. Публикуется только после проверки администратором."""

    class Status(models.TextChoices):
        PENDING = "pending", "На проверке"
        PUBLISHED = "published", "Опубликован"
        REJECTED = "rejected", "Отклонён"

    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name="reviews", verbose_name="Автосалон")
    author_name = models.CharField("Имя", max_length=80)
    rating = models.PositiveSmallIntegerField(
        "Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("Отзыв", max_length=2000)
    status = models.CharField(
        "Статус", max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Отзыв о салоне"
        verbose_name_plural = "Отзывы о салонах"
        indexes = [models.Index(fields=("dealer", "status"))]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="dealer_review_rating_1_5",
            ),
        ]

    def __str__(self):
        return f"{self.dealer} — {self.rating}★ ({self.get_status_display()})"
