import re
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.common.serializers import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_FORMATS,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_SIZE_BYTES,
    ValidatedImageField,
)

from apps.common.media import FULL_TRANSFORM, THUMB_TRANSFORM, cloudinary_variant, file_url
from apps.common.serializers import MAX_UPLOAD_PHOTO_BYTES

from .models import (
    DEFAULT_LISTING_DAYS,
    LISTING_DURATIONS,
    Brand,
    Car,
    CarImage,
    City,
    Model,
    listing_expiry,
)

MAX_IMAGES_PER_CAR = 15
MIN_CAR_YEAR = 1980
PRICE_DROP_WINDOW = timedelta(days=30)
PRICE_HISTORY_LIMIT = 10


def get_active_promotions(car):
    from django.utils import timezone
    from apps.payments.models import Promotion
    return Promotion.objects.filter(
        car=car,
        is_active=True,
        expires_at__gt=timezone.now(),
    ).values("promotion_type", "expires_at")

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
MAX_IMAGE_BATCH_SIZE_BYTES = 30 * 1024 * 1024


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        fields = (
            "id",
            "brand",
            "name",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name", "slug", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CarImageSerializer(serializers.ModelSerializer):
    """Фото машины. image — оригинал, url — w_1600 (f_auto,q_auto), thumb — w_400."""
    url = serializers.SerializerMethodField()
    thumb = serializers.SerializerMethodField()

    class Meta:
        model = CarImage
        fields = (
            "id",
            "image",
            "url",
            "thumb",
            "position",
            "is_cover",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_url(self, obj):
        return cloudinary_variant(file_url(obj.image, self.context.get("request")), FULL_TRANSFORM)

    def get_thumb(self, obj):
        return cloudinary_variant(file_url(obj.image, self.context.get("request")), THUMB_TRANSFORM)


class CarImageUpdateSerializer(serializers.Serializer):
    is_cover = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Укажите, нужно ли назначить фотографию главной."
            )
        return attrs


class CarImageReorderSerializer(serializers.Serializer):
    image_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=MAX_IMAGES_PER_CAR,
    )

    def validate_image_ids(self, image_ids):
        if len(image_ids) != len(set(image_ids)):
            raise serializers.ValidationError(
                "Идентификаторы фотографий не должны повторяться."
            )
        return image_ids


class CarImagesUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=ValidatedImageField(max_size=MAX_UPLOAD_PHOTO_BYTES),
        allow_empty=False,
        max_length=MAX_IMAGES_PER_CAR,
    )

    def validate_images(self, images):
        if sum(image.size for image in images) > MAX_IMAGE_BATCH_SIZE_BYTES:
            raise serializers.ValidationError(
                "Общий размер фотографий в запросе не должен превышать 30 МБ."
            )
        return images


class CarOwnerSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(read_only=True)

    class Meta:
        from apps.accounts.models import User
        model = User
        fields = ("id", "first_name", "last_name", "profile_photo")


class CarDealerSerializer(serializers.Serializer):
    """Вложенный блок салона в карточке машины."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.CharField(read_only=True)
    logo = serializers.SerializerMethodField()
    phone = serializers.CharField(read_only=True)
    whatsapp = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    city_name = serializers.SerializerMethodField()

    def get_city_name(self, obj):
        return obj.city.name if obj.city else None

    def get_logo(self, obj):
        return cloudinary_variant(
            file_url(obj.logo, self.context.get("request")), "f_auto,q_auto,c_limit,w_200"
        )


class CarSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="model.brand.name", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    owner_detail = CarOwnerSerializer(source="owner", read_only=True)
    # dealer ВСЕГДА выставляется на сервере (perform_create), из тела запроса игнорируется
    dealer = serializers.PrimaryKeyRelatedField(read_only=True)
    contact_phone = serializers.CharField(max_length=16, required=False, allow_blank=True)
    dealer_detail = CarDealerSerializer(source="dealer", read_only=True)
    images = CarImageSerializer(many=True, read_only=True)
    is_top = serializers.SerializerMethodField()
    is_highlighted = serializers.SerializerMethodField()
    is_urgent = serializers.SerializerMethodField()
    promotions = serializers.SerializerMethodField()
    price_drop = serializers.SerializerMethodField()
    price_history = serializers.SerializerMethodField()
    # Срок размещения в днях (0 — без срока). При создании по умолчанию 30.
    duration_days = serializers.ChoiceField(
        choices=(0, *LISTING_DURATIONS), write_only=True, required=False
    )
    is_expired = serializers.SerializerMethodField()

    def get_is_expired(self, obj):
        return obj.is_expired

    def _history(self, obj):
        # Использует prefetch_related("price_history"), новые записи — первыми
        return list(obj.price_history.all())

    def get_price_drop(self, obj):
        """Старая цена, если последнее изменение было снижением за последние 30 дней."""
        history = self._history(obj)
        if len(history) < 2:
            return None
        current, previous = history[0], history[1]
        if (
            current.currency != previous.currency
            or current.currency != obj.currency
            or previous.price <= obj.price
            or current.created_at < timezone.now() - PRICE_DROP_WINDOW
        ):
            return None
        return {
            "old_price": str(previous.price),
            "currency": previous.currency,
            "changed_at": current.created_at,
        }

    def get_price_history(self, obj):
        if not self.context.get("include_price_history"):
            return None
        return [
            {"price": str(item.price), "currency": item.currency, "changed_at": item.created_at}
            for item in self._history(obj)[:PRICE_HISTORY_LIMIT]
        ]

    def get_is_top(self, obj):
        from django.utils import timezone
        from apps.payments.models import Promotion
        return Promotion.objects.filter(
            car=obj, promotion_type="top", is_active=True, expires_at__gt=timezone.now()
        ).exists()

    def get_is_highlighted(self, obj):
        from django.utils import timezone
        from apps.payments.models import Promotion
        return Promotion.objects.filter(
            car=obj, promotion_type="highlight", is_active=True, expires_at__gt=timezone.now()
        ).exists()

    def get_is_urgent(self, obj):
        from django.utils import timezone
        from apps.payments.models import Promotion
        return Promotion.objects.filter(
            car=obj, promotion_type="urgent", is_active=True, expires_at__gt=timezone.now()
        ).exists()

    def get_promotions(self, obj):
        from django.utils import timezone
        from apps.payments.models import Promotion
        promos = Promotion.objects.filter(
            car=obj, is_active=True, expires_at__gt=timezone.now()
        ).values("promotion_type", "expires_at")
        return list(promos)

    class Meta:
        model = Car
        fields = (
            "id",
            "owner",
            "owner_detail",
            "dealer",
            "dealer_detail",
            "brand",
            "model",
            "model_name",
            "city",
            "city_name",
            "year",
            "price",
            "currency",
            "mileage",
            "engine_volume",
            "engine_type",
            "transmission",
            "drive_type",
            "body_type",
            "condition",
            "color",
            "description",
            "contact_phone",
            "status",
            "views_count",
            "phone_views",
            "whatsapp_clicks",
            "is_top",
            "is_highlighted",
            "is_urgent",
            "promotions",
            "price_drop",
            "price_history",
            "published_at",
            "expires_at",
            "duration_days",
            "is_expired",
            "created_at",
            "updated_at",
            "images",
        )
        read_only_fields = (
            "expires_at",
            "is_expired",
            "id",
            "owner",
            "owner_detail",
            "dealer",
            "dealer_detail",
            "brand",
            "model_name",
            "city_name",
            "views_count",
            "phone_views",
            "whatsapp_clicks",
            "price_drop",
            "price_history",
            "is_top",
            "is_highlighted",
            "is_urgent",
            "promotions",
            "published_at",
            "created_at",
            "updated_at",
            "images",
        )

    def validate_model(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Нельзя создать объявление для неактивной модели."
            )
        if not value.brand.is_active:
            raise serializers.ValidationError(
                "Нельзя создать объявление для неактивной марки."
            )
        return value

    def validate_price(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Цена должна быть больше нуля.")
        return value

    def validate_year(self, value):
        max_year = timezone.now().year + 1
        if not MIN_CAR_YEAR <= value <= max_year:
            raise serializers.ValidationError(
                f"Год выпуска должен быть от {MIN_CAR_YEAR} до {max_year}."
            )
        return value

    def validate_contact_phone(self, value):
        value = (value or "").replace(" ", "").replace("-", "")
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError("Введите телефон в международном формате.")
        return value

    def update(self, instance, validated_data):
        days = validated_data.pop("duration_days", None)
        if days is not None:
            validated_data["expires_at"] = listing_expiry(days)
        elif validated_data.get("status") == Car.Status.ACTIVE and instance.is_expired:
            # Публикуют снова истёкшее объявление без выбора срока — срок по умолчанию
            validated_data["expires_at"] = listing_expiry(DEFAULT_LISTING_DAYS)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data["expires_at"] = listing_expiry(
            validated_data.pop("duration_days", DEFAULT_LISTING_DAYS)
        )
        # Телефон по умолчанию — телефон салона
        if not validated_data.get("contact_phone"):
            dealer = validated_data.get("dealer")
            fallback = re.sub(r"[^\d+]", "", (dealer.phone or dealer.whatsapp) if dealer else "")
            if not PHONE_RE.match(fallback):
                raise serializers.ValidationError(
                    {"contact_phone": "Укажите телефон или заполните телефон в профиле салона."}
                )
            validated_data["contact_phone"] = fallback
        return super().create(validated_data)

    def validate_city(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Нельзя создать объявление для неактивного города."
            )
        return value


# ── Публичная выдача: без телефонов и статистики салона ───────────────────

class PublicCarDealerSerializer(CarDealerSerializer):
    phone = None
    whatsapp = None


class PublicCarSerializer(CarSerializer):
    """
    Номер телефона и WhatsApp не отдаются в каталоге — только по запросу
    POST /api/cars/<id>/contacts/ (кнопка «Показать номер»), который считает клики.
    """

    dealer_detail = PublicCarDealerSerializer(source="dealer", read_only=True)
    has_phone = serializers.SerializerMethodField()
    has_whatsapp = serializers.SerializerMethodField()

    class Meta(CarSerializer.Meta):
        fields = tuple(
            f for f in CarSerializer.Meta.fields
            if f not in ("contact_phone", "phone_views", "whatsapp_clicks", "duration_days")
        ) + ("has_phone", "has_whatsapp")
        read_only_fields = fields

    def get_has_phone(self, obj):
        return bool(obj.contact_phone or obj.dealer.phone)

    def get_has_whatsapp(self, obj):
        return bool(obj.contact_phone or obj.dealer.whatsapp or obj.dealer.phone)


class ContactRevealSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("phone", "whatsapp"))
