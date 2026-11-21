from django.db.models import BooleanField, Exists, ExpressionWrapper, F, OuterRef
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.dealers.permissions import PublicReadOnly

from .filters import CarFilter
from .models import Brand, Car, City, Model, not_expired_q
from .pagination import CarPagination
from .serializers import (
    BrandSerializer,
    CitySerializer,
    ContactRevealSerializer,
    ModelSerializer,
    PublicCarSerializer,
)


def public_cars_queryset():
    """Публично видны только активные объявления активных салонов с оплаченным тарифом."""
    from apps.subscriptions.services import active_subscription_exists

    return (
        Car.objects.filter(status=Car.Status.ACTIVE, dealer__is_active=True)
        .filter(not_expired_q())
        .filter(active_subscription_exists("dealer"))
        .select_related("owner", "dealer", "dealer__city", "model", "model__brand", "city")
        .prefetch_related("images", "price_history")
    )


def is_own_dealer_view(request, car):
    return request.user.is_authenticated and request.user.dealer_id == car.dealer_id


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

    serializer_class = PublicCarSerializer
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
    throttle_scope = None  # задаётся для действия contacts

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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["include_price_history"] = self.action == "retrieve"
        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not is_own_dealer_view(request, instance):
            Car.objects.filter(pk=instance.pk).update(views_count=F("views_count") + 1)
            instance.views_count = (instance.views_count or 0) + 1
        return Response(self.get_serializer(instance).data)

    @action(
        detail=True,
        methods=("post",),
        url_path="contacts",
        permission_classes=(AllowAny,),
        throttle_classes=(ScopedRateThrottle,),
        throttle_scope="contacts",
    )
    def contacts(self, request, pk=None):
        """«Показать номер» / «Написать в WhatsApp»: отдаёт контакты и считает клик."""
        serializer = ContactRevealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = self.get_object()
        if not is_own_dealer_view(request, car):
            counter = "phone_views" if serializer.validated_data["kind"] == "phone" else "whatsapp_clicks"
            Car.objects.filter(pk=car.pk).update(**{counter: F(counter) + 1})
        phone = car.dealer.phone or car.contact_phone
        whatsapp = car.dealer.whatsapp or car.contact_phone
        return Response({"phone": phone or None, "whatsapp": whatsapp or None})
