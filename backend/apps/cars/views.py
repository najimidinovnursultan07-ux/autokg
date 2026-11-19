from django.db.models import BooleanField, Exists, ExpressionWrapper, F, OuterRef
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.dealers.permissions import PublicReadOnly

from .filters import CarFilter
from .models import Brand, Car, City, Model
from .pagination import CarPagination
from .serializers import (
    BrandSerializer,
    CarSerializer,
    CitySerializer,
    ModelSerializer,
)


def public_cars_queryset():
    """Публично видны только активные объявления активных салонов."""
    return (
        Car.objects.filter(status=Car.Status.ACTIVE, dealer__is_active=True)
        .select_related("owner", "dealer", "dealer__city", "model", "model__brand", "city")
        .prefetch_related("images")
    )


class BrandViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Brand.objects.filter(is_active=True)
    serializer_class = BrandSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Model.objects.filter(
        is_active=True,
        brand__is_active=True,
    ).select_related("brand")
    serializer_class = ModelSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    filterset_fields = ("brand",)


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.filter(is_active=True)
    serializer_class = CitySerializer
    permission_classes = (AllowAny,)
    pagination_class = None


SAFE_ORDERING = {
    "price", "-price",
    "published_at", "-published_at",
    "created_at", "-created_at",
    "year", "-year",
    "mileage", "-mileage",
}


class CarViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Публичный каталог: только чтение. Создание и редактирование объявлений —
    через /api/dashboard/cars/ (салоны) и /api/admin/cars/ (администратор).
    POST/PUT/PATCH/DELETE здесь: аноним → 401, авторизованный → 403.
    """

    serializer_class = CarSerializer
    pagination_class = CarPagination
    permission_classes = (PublicReadOnly,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = CarFilter
    search_fields = (
        "model__brand__name",
        "model__name",
        "city__name",
        "dealer__name",
        "description",
    )
    ordering_fields = tuple(f for f in SAFE_ORDERING if not f.startswith("-"))
    ordering = ("-published_at", "-created_at")
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        qs = public_cars_queryset()
        if self.action != "list":
            return qs
        from apps.payments.models import Promotion

        active_top = Promotion.objects.filter(
            car=OuterRef("pk"),
            promotion_type="top",
            is_active=True,
            expires_at__gt=timezone.now(),
        )
        qs = qs.annotate(
            has_top=ExpressionWrapper(Exists(active_top), output_field=BooleanField())
        )
        # ТОП всегда первый — пользовательская сортировка применяется вторым ключом
        user_ordering = self.request.query_params.get("ordering", "-published_at")
        second = user_ordering if user_ordering in SAFE_ORDERING else "-published_at"
        return qs.order_by("-has_top", second, "-created_at")

    def filter_queryset(self, queryset):
        # OrderingFilter не должен перебивать порядок «ТОП первым»
        for backend in (DjangoFilterBackend, SearchFilter):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_authenticated or request.user.dealer_id != instance.dealer_id:
            Car.objects.filter(pk=instance.pk).update(views_count=F("views_count") + 1)
            instance.views_count = (instance.views_count or 0) + 1
        return Response(self.get_serializer(instance).data)
