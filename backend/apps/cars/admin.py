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
        "currency",
        "city",
        "dealer",
        "status",
        "created_at",
    )
    list_filter = ("status", "dealer", "model__brand", "city", "year")
    list_editable = ("status",)
    list_select_related = ("model", "model__brand", "city", "dealer")
    search_fields = (
        "model__brand__name",
        "model__name",
        "dealer__name",
        "owner__email",
        "contact_phone",
    )
    autocomplete_fields = ("dealer",)
    readonly_fields = ("id", "created_at", "updated_at", "published_at", "views_count")
    actions = ("move_to_dealer",)
    inlines = (CarImageInline,)

    @admin.display(description="Марка", ordering="model__brand__name")
    def brand_name(self, obj):
        return obj.model.brand.name

    @admin.action(description="Перенести выбранные объявления в салон…")
    def move_to_dealer(self, request, queryset):
        from django import forms
        from django.shortcuts import render

        from apps.dealers.models import Dealer

        class MoveForm(forms.Form):
            dealer = forms.ModelChoiceField(queryset=Dealer.objects.all(), label="Салон")

        if "apply" in request.POST:
            form = MoveForm(request.POST)
            if form.is_valid():
                count = queryset.update(dealer=form.cleaned_data["dealer"])
                self.message_user(request, f"Перенесено объявлений: {count}.")
                return None
        else:
            form = MoveForm()
        return render(
            request,
            "admin/cars/move_to_dealer.html",
            {**self.admin_site.each_context(request), "form": form, "cars": queryset,
             "title": "Перенести в салон"},
        )


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ("id", "car", "position", "is_cover", "created_at")
    list_filter = ("is_cover",)
    search_fields = ("car__id",)
    raw_id_fields = ("car",)
