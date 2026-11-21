from django.utils import timezone
from rest_framework import serializers

from apps.dealers.models import Dealer

from .models import PERIOD_MONTHS, Plan, PlanRequest, Subscription


class PlanSerializer(serializers.ModelSerializer):
    stats_level_label = serializers.CharField(source="get_stats_level_display", read_only=True)

    class Meta:
        model = Plan
        fields = (
            "id", "code", "name", "price_month", "price_3_months", "price_12_months",
            "max_active_cars", "top_per_month", "highlight_per_month", "urgent_per_month",
            "has_badge", "stats_level", "stats_level_label", "has_excel_import",
            "list_priority", "featured_on_home", "priority_support",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    days_left = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ("id", "plan", "starts_at", "expires_at", "is_trial", "months", "days_left")

    def get_days_left(self, obj):
        seconds = (obj.expires_at - timezone.now()).total_seconds()
        return max(0, int(-(-seconds // 86400)))  # округление вверх


class AdminSubscriptionSerializer(SubscriptionSerializer):
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)
    payment_method_label = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + (
            "dealer", "dealer_name", "amount", "payment_method", "payment_method_label",
            "note", "created_by_email", "created_at",
        )


class ActivateSubscriptionSerializer(serializers.Serializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects.all())
    months = serializers.ChoiceField(choices=PERIOD_MONTHS)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=0)
    payment_method = serializers.ChoiceField(
        choices=Subscription.PaymentMethod.choices, required=False, allow_blank=True, default=""
    )
    note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    request_id = serializers.IntegerField(required=False, allow_null=True)


class PlanRequestSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlanRequest
        fields = ("id", "plan", "plan_name", "months", "comment", "status", "status_label", "created_at")
        read_only_fields = ("id", "status", "created_at")

    def validate_months(self, value):
        if value not in PERIOD_MONTHS:
            raise serializers.ValidationError("Срок: 1, 3 или 12 месяцев.")
        return value

    def validate_plan(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Этот тариф сейчас недоступен.")
        return value


class AdminPlanRequestSerializer(PlanRequestSerializer):
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    dealer_phone = serializers.CharField(source="dealer.phone", read_only=True)
    dealer_whatsapp = serializers.CharField(source="dealer.whatsapp", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True, default=None)

    class Meta(PlanRequestSerializer.Meta):
        fields = PlanRequestSerializer.Meta.fields + (
            "dealer", "dealer_name", "dealer_phone", "dealer_whatsapp", "created_by_email", "processed_at",
        )
        read_only_fields = tuple(
            f for f in fields if f != "status"
        )


class PromoteSerializer(serializers.Serializer):
    car_id = serializers.UUIDField()
    promotion_type = serializers.ChoiceField(choices=("top", "highlight", "urgent"))
