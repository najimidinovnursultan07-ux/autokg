from django.contrib import admin

from .models import AdBanner, AdDailyStat


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
        "title", "advertiser", "placement", "starts_on", "ends_on", "is_active", "impressions", "clicks",
    )
    list_filter = ("placement", "is_active")
    list_editable = ("is_active",)
    search_fields = ("title", "advertiser", "advertiser_contact")
    readonly_fields = ("impressions", "clicks", "created_at", "updated_at")
    inlines = (AdDailyStatInline,)
