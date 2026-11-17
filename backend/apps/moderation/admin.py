from django.contrib import admin

from .models import ModerationEvent


@admin.register(ModerationEvent)
class ModerationEventAdmin(admin.ModelAdmin):
    list_display = ("car", "actor", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("car__model__brand__name", "car__model__name", "actor__email")
    readonly_fields = ("car", "actor", "action", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
