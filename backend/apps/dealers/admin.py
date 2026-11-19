from django.contrib import admin
from django.db.models import Count

from apps.accounts.models import User

from .models import Dealer


class ManagerInline(admin.TabularInline):
    model = User
    fk_name = "dealer"
    fields = ("email", "first_name", "last_name", "is_active", "last_login")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True
    verbose_name = "Менеджер"
    verbose_name_plural = "Менеджеры"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "city", "phone", "is_active", "cars_total", "created_at")
    list_filter = ("is_active", "city")
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "phone")
    readonly_fields = ("created_at", "updated_at")
    inlines = (ManagerInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(cars_total=Count("cars"))

    @admin.display(description="Объявлений", ordering="cars_total")
    def cars_total(self, obj):
        return obj.cars_total
