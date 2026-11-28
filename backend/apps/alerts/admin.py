from django.contrib import admin

from .models import PriceWatch, SavedSearch, TelegramChat


@admin.register(TelegramChat)
class TelegramChatAdmin(admin.ModelAdmin):
    list_display = ("__str__", "first_name", "is_blocked", "created_at")
    list_filter = ("is_blocked",)
    search_fields = ("username", "first_name", "chat_id")


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("title", "chat", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title",)
    readonly_fields = ("token", "filters", "chat", "created_at", "subscribed_at")


@admin.register(PriceWatch)
class PriceWatchAdmin(admin.ModelAdmin):
    list_display = ("car", "chat", "last_price", "currency", "is_active", "created_at")
    list_filter = ("is_active",)
    readonly_fields = ("token", "car", "chat", "created_at")
