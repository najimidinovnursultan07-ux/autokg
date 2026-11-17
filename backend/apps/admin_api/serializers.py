from rest_framework import serializers

from apps.accounts.models import User
from apps.cars.models import Car


class AdminUserSerializer(serializers.ModelSerializer):
    listings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_active",
            "date_joined",
            "last_login",
            "listings_count",
        )
        read_only_fields = fields


class AdminCarSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    brand = serializers.CharField(source="model.brand.name", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = Car
        fields = (
            "id",
            "owner",
            "owner_email",
            "brand",
            "model",
            "model_name",
            "city",
            "city_name",
            "year",
            "price",
            "mileage",
            "status",
            "created_at",
            "published_at",
        )
        read_only_fields = fields
