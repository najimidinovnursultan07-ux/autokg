from rest_framework import serializers

from apps.common.serializers import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_FORMATS,
    MAX_IMAGE_PIXELS,
    MAX_IMAGE_SIZE_BYTES,
    ValidatedImageField,
)

from .models import Brand, Car, CarImage, City, Model

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
    class Meta:
        model = CarImage
        fields = (
            "id",
            "image",
            "position",
            "is_cover",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


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
        max_length=20,
    )

    def validate_image_ids(self, image_ids):
        if len(image_ids) != len(set(image_ids)):
            raise serializers.ValidationError(
                "Идентификаторы фотографий не должны повторяться."
            )
        return image_ids


class CarImagesUploadSerializer(serializers.Serializer):
    images = serializers.ListField(
        child=ValidatedImageField(),
        allow_empty=False,
        max_length=10,
    )

    def validate_images(self, images):
        if sum(image.size for image in images) > MAX_IMAGE_BATCH_SIZE_BYTES:
            raise serializers.ValidationError(
                "Общий размер фотографий в запросе не должен превышать 30 МБ."
            )
        return images


class RejectCarSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, allow_blank=False)


class CarSerializer(serializers.ModelSerializer):
    brand = serializers.CharField(source="model.brand.name", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    images = CarImageSerializer(many=True, read_only=True)

    class Meta:
        model = Car
        fields = (
            "id",
            "owner",
            "brand",
            "model",
            "model_name",
            "city",
            "city_name",
            "year",
            "price",
            "mileage",
            "engine_volume",
            "engine_type",
            "transmission",
            "drive_type",
            "body_type",
            "condition",
            "description",
            "contact_phone",
            "status",
            "views_count",
            "published_at",
            "created_at",
            "updated_at",
            "images",
        )
        read_only_fields = (
            "id",
            "owner",
            "brand",
            "model_name",
            "city_name",
            "status",
            "views_count",
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

    def validate_city(self, value):
        if not value.is_active:
            raise serializers.ValidationError(
                "Нельзя создать объявление для неактивного города."
            )
        return value
