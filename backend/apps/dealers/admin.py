from django.contrib import admin
from .models import Dealer


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "city", "is_active", "created_at")
    list_filter = ("is_active", "city")
    search_fields = ("name", "slug", "phone")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
