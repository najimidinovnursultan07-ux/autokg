from rest_framework import serializers

from apps.accounts.models import User
from apps.cars.models import Car
from apps.common.media import THUMB_TRANSFORM, cloudinary_variant, file_url
from apps.dealers.models import Dealer


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
    """Модерация: админ может менять статус и переносить машину в другой салон."""

    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    brand = serializers.CharField(source="model.brand.name", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all(), required=False)
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    dealer_slug = serializers.CharField(source="dealer.slug", read_only=True)
    dealer_is_active = serializers.BooleanField(source="dealer.is_active", read_only=True)
    thumb = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = (
            "id",
            "owner",
            "owner_email",
            "dealer",
            "dealer_name",
            "dealer_slug",
            "dealer_is_active",
            "brand",
            "model",
            "model_name",
            "city",
            "city_name",
            "year",
            "price",
            "currency",
            "mileage",
            "status",
            "views_count",
            "thumb",
            "created_at",
            "published_at",
        )
        read_only_fields = tuple(f for f in fields if f not in ("status", "dealer"))

    def get_thumb(self, obj):
        images = list(obj.images.all())
        cover = next((i for i in images if i.is_cover), images[0] if images else None)
        if cover is None:
            return None
        return cloudinary_variant(file_url(cover.image, self.context.get("request")), THUMB_TRANSFORM)
