from django.contrib import admin
from .models import Payment, Promotion


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "car", "service_type", "amount", "status", "created_at")
    list_filter = ("status", "service_type", "provider")
    search_fields = ("user__email", "transaction_id")
    readonly_fields = ("id", "created_at", "updated_at", "paid_at")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("id", "car", "promotion_type", "is_active", "starts_at", "expires_at")
    list_filter = ("promotion_type", "is_active")
    readonly_fields = ("created_at",)
