from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "dealer", "is_active")
    list_filter = ("role", "is_active", "dealer")
    autocomplete_fields = ("dealer",)
    search_fields = ("email", "first_name", "last_name", "phone")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личные данные", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Права",
            {
                "fields": (
                    "role",
                    "dealer",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "dealer",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
