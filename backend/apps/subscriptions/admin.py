from django.contrib import admin

from .models import Plan, PlanRequest, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price_month", "max_active_cars", "top_per_month", "highlight_per_month", "is_active")
    list_editable = ("is_active",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("dealer", "plan", "starts_at", "expires_at", "is_trial", "amount", "payment_method")
    list_filter = ("plan", "is_trial", "payment_method")
    search_fields = ("dealer__name",)
    readonly_fields = ("created_at", "created_by")


@admin.register(PlanRequest)
class PlanRequestAdmin(admin.ModelAdmin):
    list_display = ("dealer", "plan", "months", "status", "created_at")
    list_filter = ("status", "plan")
    search_fields = ("dealer__name",)
