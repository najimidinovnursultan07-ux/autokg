from django.contrib import admin

from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "car", "created_at")
    search_fields = ("user__email", "car__model__brand__name", "car__model__name")
    readonly_fields = ("user", "car", "created_at")
