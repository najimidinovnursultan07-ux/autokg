import django_filters

from .models import Car


class CarFilter(django_filters.FilterSet):
    brand = django_filters.NumberFilter(field_name="model__brand_id")
    model = django_filters.NumberFilter(field_name="model_id")
    city = django_filters.NumberFilter(field_name="city_id")
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte",
    )
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte",
    )
    min_year = django_filters.NumberFilter(
        field_name="year",
        lookup_expr="gte",
    )
    max_year = django_filters.NumberFilter(
        field_name="year",
        lookup_expr="lte",
    )
    min_mileage = django_filters.NumberFilter(
        field_name="mileage",
        lookup_expr="gte",
    )
    max_mileage = django_filters.NumberFilter(
        field_name="mileage",
        lookup_expr="lte",
    )

    class Meta:
        model = Car
        fields = (
            "brand",
            "model",
            "city",
            "engine_type",
            "transmission",
            "drive_type",
            "body_type",
            "condition",
            "status",
        )
