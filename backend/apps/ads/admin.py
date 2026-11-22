from django.contrib import admin

from .models import AdBanner, AdDailyStat, AdPlacementPrice


class AdDailyStatInline(admin.TabularInline):
    model = AdDailyStat
    fields = ("date", "impressions", "clicks")
    readonly_fields = fields
    extra = 0
    can_delete = False
    ordering = ("-date",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    list_display = (
        "title", "advertiser", "placement", "starts_on", "ends_on", "price", "is_paid", "is_active",
        "impressions", "clicks",
    )
    list_filter = ("placement", "is_active", "is_paid")
    list_editable = ("is_active",)
    search_fields = ("title", "advertiser", "advertiser_contact")
    readonly_fields = ("impressions", "clicks", "created_at", "updated_at")
    inlines = (AdDailyStatInline,)


@admin.register(AdPlacementPrice)
class AdPlacementPriceAdmin(admin.ModelAdmin):
    list_display = ("placement", "price_week", "price_month", "updated_at")
    list_editable = ("price_week", "price_month")
