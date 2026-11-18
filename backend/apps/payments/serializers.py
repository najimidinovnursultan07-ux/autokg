from django.utils import timezone
from rest_framework import serializers

from .models import SERVICE_DURATIONS, SERVICE_PRICES, Payment, PaymentStatus, Promotion, ServiceType


class ServicePriceSerializer(serializers.Serializer):
    service_type = serializers.ChoiceField(choices=ServiceType.choices)
    label = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    duration_days = serializers.SerializerMethodField()
    currency = serializers.CharField(default="KGS")

    def get_label(self, obj):
        return dict(ServiceType.choices).get(obj, obj)

    def get_amount(self, obj):
        return str(SERVICE_PRICES.get(obj, "0.00"))

    def get_duration_days(self, obj):
        return SERVICE_DURATIONS.get(obj, 7)


class PromotionSerializer(serializers.ModelSerializer):
    promotion_type_label = serializers.CharField(source="get_promotion_type_display", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Promotion
        fields = (
            "id",
            "promotion_type",
            "promotion_type_label",
            "starts_at",
            "expires_at",
            "is_active",
            "is_expired",
            "created_at",
        )


class PaymentSerializer(serializers.ModelSerializer):
    service_type_label = serializers.CharField(source="get_service_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    car_title = serializers.SerializerMethodField()
    promotion = PromotionSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "car",
            "car_title",
            "service_type",
            "service_type_label",
            "amount",
            "currency",
            "provider",
            "transaction_id",
            "status",
            "status_label",
            "promotion",
            "created_at",
            "paid_at",
        )
        read_only_fields = fields

    def get_car_title(self, obj):
        car = obj.car
        try:
            return f"{car.model.brand.name} {car.model.name} {car.year}"
        except Exception:
            return str(car.id)


class CreatePaymentSerializer(serializers.Serializer):
    car_id = serializers.UUIDField()
    service_type = serializers.ChoiceField(choices=ServiceType.choices)

    def validate_service_type(self, value):
        if value not in SERVICE_PRICES:
            raise serializers.ValidationError("Неизвестный тип услуги.")
        return value
