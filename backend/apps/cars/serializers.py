import re

from django.utils import timezone
from rest_framework import serializers

from apps.common.serializers import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_FORMATS,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_SIZE_BYTES,
    ValidatedImageField,
)

from apps.common.media import file_url
from apps.common.serializers import MAX_UPLOAD_PHOTO_BYTES

from .models import Brand, Car, CarImage, City, Model

MAX_IMAGES_PER_CAR = 15
MIN_CAR_YEAR = 1980


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
    """Фото машины. url — WebP до 1280px, thumb — превью 400×300 (старые фото: оригинал)."""
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
        return file_url(obj.image, self.context.get("request"))

    def get_thumb(self, obj):
        return file_url(obj.thumbnail or obj.image, self.context.get("request"))


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
        return file_url(obj.logo, self.context.get("request"))


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
            "is_top",
            "is_highlighted",
            "is_urgent",
            "promotions",
            "published_at",
            "created_at",
            "updated_at",
            "images",
        )
        read_only_fields = (
            "id",
            "owner",
            "owner_detail",
            "dealer",
            "dealer_detail",
            "brand",
            "model_name",
            "city_name",
            "views_count",
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

    def create(self, validated_data):
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
