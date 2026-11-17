from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User
from apps.accounts.tokens import revoke_user_refresh_tokens
from apps.cars.filters import CarFilter
from apps.cars.models import Brand, Car, City, Model
from apps.cars.pagination import CarPagination
from apps.cars.serializers import BrandSerializer, CitySerializer, ModelSerializer
from apps.common.permissions import IsAutoKGAdmin
from apps.moderation.models import ModerationEvent

from .serializers import AdminCarSerializer, AdminUserSerializer


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminStatsView(APIView):
    permission_classes = (IsAutoKGAdmin,)

    def get(self, request):
        user_counts = User.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            blocked=Count("id", filter=Q(is_active=False)),
        )
        car_counts = Car.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Car.Status.PENDING)),
            published=Count("id", filter=Q(status=Car.Status.PUBLISHED)),
            inactive=Count("id", filter=Q(status=Car.Status.INACTIVE)),
            removed=Count("id", filter=Q(status=Car.Status.REMOVED)),
        )
        return Response({"users": user_counts, "cars": car_counts})


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = (IsAutoKGAdmin,)
    pagination_class = AdminPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("is_active", "role")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering_fields = ("email", "date_joined", "last_login", "listings_count")
    ordering = ("-date_joined",)

    def get_queryset(self):
        return User.objects.annotate(listings_count=Count("cars"))

    def _set_active(self, request, pk, *, active):
        user = get_object_or_404(self.get_queryset(), pk=pk)
        if user.pk == request.user.pk:
            raise ValidationError({"detail": "Нельзя изменять состояние собственного аккаунта."})
        if user.role == User.Role.ADMIN:
            raise ValidationError({"detail": "Управление аккаунтами администраторов запрещено."})
        if user.is_active != active:
            user.is_active = active
            user.save(update_fields=("is_active", "updated_at"))
            if not active:
                revoke_user_refresh_tokens(user)
        return Response(self.get_serializer(user).data)

    @action(detail=True, methods=("post",))
    def block(self, request, pk=None):
        return self._set_active(request, pk, active=False)

    @action(detail=True, methods=("post",))
    def unblock(self, request, pk=None):
        return self._set_active(request, pk, active=True)


class AdminCarViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AdminCarSerializer
    permission_classes = (IsAutoKGAdmin,)
    pagination_class = CarPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = CarFilter
    search_fields = (
        "model__brand__name",
        "model__name",
        "owner__email",
        "contact_phone",
    )
    ordering_fields = ("created_at", "published_at", "price", "year")
    ordering = ("-created_at",)
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return Car.objects.select_related(
            "owner",
            "model",
            "model__brand",
            "city",
        )

    def perform_destroy(self, instance):
        with transaction.atomic():
            car = Car.objects.select_for_update().get(pk=instance.pk)
            if car.status != Car.Status.REMOVED:
                car.status = Car.Status.REMOVED
                car.save(update_fields=("status", "updated_at"))
                ModerationEvent.objects.create(
                    car=car,
                    actor=self.request.user,
                    action=ModerationEvent.Action.REMOVED,
                )


class ProtectedCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAutoKGAdmin,)
    pagination_class = AdminPagination
    filter_backends = (SearchFilter, OrderingFilter)
    ordering = ("name",)
    http_method_names = ("get", "post", "put", "patch", "delete", "head", "options")
    protected_delete_message = (
        "Элемент используется объявлениями и не может быть удалён. "
        "Деактивируйте его вместо удаления."
    )

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": self.protected_delete_message},
                status=status.HTTP_409_CONFLICT,
            )


class AdminBrandViewSet(ProtectedCatalogViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    search_fields = ("name", "slug")
    ordering_fields = ("name", "created_at")


class AdminModelViewSet(ProtectedCatalogViewSet):
    queryset = Model.objects.select_related("brand")
    serializer_class = ModelSerializer
    search_fields = ("name", "slug", "brand__name")
    ordering_fields = ("name", "created_at")
    filterset_fields = ("brand", "is_active")
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)


class AdminCityViewSet(ProtectedCatalogViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    search_fields = ("name", "slug")
    ordering_fields = ("name", "created_at")
