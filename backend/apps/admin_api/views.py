from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
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
from apps.common.permissions import IsAutoBuyAdmin
from apps.dealers.models import Dealer

from .report import build_report, build_report_xlsx, parse_period
from .report_pdf import build_report_pdf
from .serializers import AdminCarSerializer, AdminUserSerializer


class AdminPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminStatsView(APIView):
    """Число салонов, объявлений и объявлений по салонам."""

    permission_classes = (IsAutoBuyAdmin,)

    def get(self, request):
        dealers = Dealer.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
        )
        cars = Car.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=Car.Status.ACTIVE)),
            hidden=Count("id", filter=Q(status=Car.Status.HIDDEN)),
            sold=Count("id", filter=Q(status=Car.Status.SOLD)),
        )
        managers = User.objects.filter(role=User.Role.DEALER).aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
        )
        by_dealer = list(
            Dealer.objects.annotate(
                total=Count("cars"),
                active=Count("cars", filter=Q(cars__status=Car.Status.ACTIVE)),
            )
            .values("id", "name", "slug", "is_active", "total", "active")
            .order_by("-total", "name")
        )
        return Response({
            "dealers": dealers,
            "cars": cars,
            "managers": managers,
            "cars_by_dealer": by_dealer,
        })


class AdminReportView(APIView):
    """Сводный отчёт по всем салонам. ?from=&to= (ГГГГ-ММ-ДД), по умолчанию текущий месяц."""

    permission_classes = (IsAutoBuyAdmin,)

    def get(self, request):
        start, end, start_dt, end_dt = parse_period(request.query_params)
        report = build_report(start_dt, end_dt)
        report["period"] = {"from": start, "to": end}
        return Response(report)


class AdminReportExportView(APIView):
    """Тот же отчёт файлом Excel: лист «Сводка» и лист «Салоны»."""

    permission_classes = (IsAutoBuyAdmin,)

    def get(self, request):
        start, end, start_dt, end_dt = parse_period(request.query_params)
        content = build_report_xlsx(build_report(start_dt, end_dt), start, end)
        response = HttpResponse(
            content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="autobuy-report-{start:%Y-%m-%d}_{end:%Y-%m-%d}.xlsx"'
        )
        return response


class AdminReportPdfView(APIView):
    """Тот же отчёт в PDF (A4 альбомная) — для печати и отправки."""

    permission_classes = (IsAutoBuyAdmin,)

    def get(self, request):
        start, end, start_dt, end_dt = parse_period(request.query_params)
        content = build_report_pdf(build_report(start_dt, end_dt), start, end)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="autobuy-report-{start:%Y-%m-%d}_{end:%Y-%m-%d}.pdf"'
        )
        return response


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = (IsAutoBuyAdmin,)
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


class AdminCarViewSet(viewsets.ModelViewSet):
    """Модерация всех объявлений: просмотр, смена статуса / салона, удаление."""

    serializer_class = AdminCarSerializer
    permission_classes = (IsAutoBuyAdmin,)
    pagination_class = CarPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = CarFilter
    search_fields = (
        "model__brand__name",
        "model__name",
        "owner__email",
        "dealer__name",
        "contact_phone",
    )
    ordering_fields = ("created_at", "published_at", "price", "year", "views_count")
    ordering = ("-created_at",)
    lookup_value_regex = "[0-9a-f-]{36}"
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Car.objects.select_related(
            "owner", "dealer", "model", "model__brand", "city"
        ).prefetch_related("images")

    def perform_update(self, serializer):
        car = serializer.save()
        if car.status == Car.Status.ACTIVE and car.published_at is None:
            car.published_at = timezone.now()
            car.save(update_fields=("published_at", "updated_at"))

    def perform_destroy(self, instance):
        # Файлы фото удаляются из Cloudinary сигналом post_delete
        instance.delete()


class ProtectedCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAutoBuyAdmin,)
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
