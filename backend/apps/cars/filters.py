import django_filters

from .models import Car


class CarFilter(django_filters.FilterSet):
    brand = django_filters.NumberFilter(field_name="model__brand_id")
    model = django_filters.NumberFilter(field_name="model_id")
    city = django_filters.NumberFilter(field_name="city_id")
    dealer = django_filters.CharFilter(field_name="dealer__slug")
    fuel = django_filters.CharFilter(field_name="engine_type")
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    year_min = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year_max = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    mileage_min = django_filters.NumberFilter(field_name="mileage", lookup_expr="gte")
    mileage_max = django_filters.NumberFilter(field_name="mileage", lookup_expr="lte")
    # Только авто, отмеченные салоном, и только если салон включил мурабаху
    murabaha = django_filters.BooleanFilter(method="filter_murabaha")

    def filter_murabaha(self, queryset, name, value):
        if value:
            return queryset.filter(murabaha_available=True, dealer__murabaha_enabled=True)
        return queryset

    class Meta:
        model = Car
        fields = (
            "brand",
            "model",
            "city",
            "dealer",
            "fuel",
            "engine_type",
            "transmission",
            "drive_type",
            "body_type",
            "condition",
            "currency",
            "status",
        )
