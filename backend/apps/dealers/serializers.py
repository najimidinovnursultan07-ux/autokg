from rest_framework import serializers
from apps.common.serializers import ValidatedImageField
from .models import Dealer


class DealerSerializer(serializers.ModelSerializer):
    logo = ValidatedImageField(required=False, allow_null=True)
    car_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "description",
            "phone", "whatsapp", "address", "city",
            "is_active", "car_count", "created_at",
        )
        read_only_fields = ("id", "slug", "car_count", "created_at")


class DealerPublicSerializer(serializers.ModelSerializer):
    """Публичный — только активные."""
    city_name = serializers.CharField(source="city.name", read_only=True, allow_null=True)
    car_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "description",
            "phone", "whatsapp", "address", "city_name",
            "car_count",
        )


class DealerProfileSerializer(serializers.ModelSerializer):
    """Для редактирования профиля дилером."""
    logo = ValidatedImageField(required=False, allow_null=True)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "description",
            "phone", "whatsapp", "address", "city",
        )
        read_only_fields = ("id", "slug")
