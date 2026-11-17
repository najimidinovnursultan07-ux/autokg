from django.contrib import admin

from .models import Brand, Car, CarImage, City, Model


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Model)
class CatalogModelAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "is_active")
    list_filter = ("brand", "is_active")
    search_fields = ("name", "brand__name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 0


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "brand_name",
        "model",
        "year",
        "price",
        "city",
        "status",
        "owner",
        "created_at",
    )
    list_filter = ("status", "model__brand", "city", "year")
    search_fields = (
        "model__brand__name",
        "model__name",
        "owner__email",
        "contact_phone",
    )
    readonly_fields = ("id", "created_at", "updated_at", "published_at")
    inlines = (CarImageInline,)

    @admin.display(description="Марка", ordering="model__brand__name")
    def brand_name(self, obj):
        return obj.model.brand.name
