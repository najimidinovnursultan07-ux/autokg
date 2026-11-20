from django.db import transaction
from django.db.models import Avg, Count, IntegerField, Max, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.tokens import revoke_user_refresh_tokens
from apps.cars.models import Car, CarImage
from apps.cars.pagination import CarPagination
from apps.cars.serializers import (
    MAX_IMAGES_PER_CAR,
    CarImageSerializer,
    CarImagesUploadSerializer,
    CarSerializer,
    PublicCarSerializer,
)
from apps.cars.views import public_cars_queryset

from .models import Dealer, DealerReview
from .permissions import IsAdminRole, IsDealerOwnerOrAdmin, IsDealerRole
from .serializers import (
    AdminDealerReviewSerializer,
    DealerProfileSerializer,
    DealerReviewCreateSerializer,
    DealerReviewSerializer,
    DealerPublicSerializer,
    DealerSerializer,
    ManagerSerializer,
    PasswordResetByAdminSerializer,
)

ACTIVE_CARS = Q(cars__status=Car.Status.ACTIVE)
DEALER_PAGE_CARS_LIMIT = 24


def with_rating(queryset):
    """Средняя оценка и число опубликованных отзывов (подзапросы — без размножения строк)."""
    published = DealerReview.objects.filter(
        dealer=OuterRef("pk"), status=DealerReview.Status.PUBLISHED
    ).values("dealer")
    return queryset.annotate(
        rating=Subquery(published.annotate(avg=Avg("rating")).values("avg")[:1]),
        reviews_count=Coalesce(
            Subquery(published.annotate(n=Count("id")).values("n")[:1], output_field=IntegerField()),
            0,
        ),
    )


# ── Публичные ──────────────────────────────────────────────────────────────

class PublicDealerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dealers = with_rating(
            Dealer.objects.filter(is_active=True)
            .annotate(car_count=Count("cars", filter=ACTIVE_CARS))
            .select_related("city")
        )
        return Response(
            DealerPublicSerializer(dealers, many=True, context={"request": request}).data
        )


class PublicDealerDetailView(APIView):
    """Салон + его последние активные машины (полный список — /api/cars/?dealer=<slug>)."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        dealer = get_object_or_404(
            with_rating(Dealer.objects.annotate(car_count=Count("cars", filter=ACTIVE_CARS)))
            .select_related("city"),
            slug=slug,
            is_active=True,
        )
        cars = public_cars_queryset().filter(dealer=dealer)[:DEALER_PAGE_CARS_LIMIT]
        ctx = {"request": request}
        return Response({
            "dealer": DealerPublicSerializer(dealer, context=ctx).data,
            "cars": PublicCarSerializer(cars, many=True, context=ctx).data,
        })


class DealerReviewListCreateView(ListCreateAPIView):
    """
    GET  — опубликованные отзывы салона.
    POST — новый отзыв; появится на сайте после проверки администратором.
    """

    permission_classes = [AllowAny]
    throttle_scope = "reviews"

    def get_throttles(self):
        # Лимит только на отправку отзывов, чтение — по общим правилам
        if self.request.method == "POST":
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_dealer(self):
        if not hasattr(self, "_dealer"):
            self._dealer = get_object_or_404(Dealer, slug=self.kwargs["slug"], is_active=True)
        return self._dealer

    def get_serializer_class(self):
        return DealerReviewCreateSerializer if self.request.method == "POST" else DealerReviewSerializer

    def get_queryset(self):
        return self.get_dealer().reviews.filter(status=DealerReview.Status.PUBLISHED)

    def create(self, request, *args, **kwargs):
        dealer = self.get_dealer()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        honeypot = serializer.validated_data.pop("website", "")
        if not honeypot:
            # Бот, заполнивший ловушку, получает тот же ответ, но отзыв не сохраняется
            serializer.save(dealer=dealer)
        return Response(
            {"detail": "Спасибо! Отзыв появится на сайте после проверки."},
            status=status.HTTP_201_CREATED,
        )


# ── Кабинет салона (role=dealer) ───────────────────────────────────────────

class DealerProfileView(APIView):
    permission_classes = [IsDealerRole]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(
            DealerProfileSerializer(request.user.dealer, context={"request": request}).data
        )

    def patch(self, request):
        serializer = DealerProfileSerializer(
            request.user.dealer,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DashboardCarViewSet(viewsets.ModelViewSet):
    """
    Объявления своего салона. Чужие объявления не попадают в queryset → 404.
    dealer и owner всегда берутся из request.user, из тела запроса игнорируются.
    """

    serializer_class = CarSerializer
    permission_classes = [IsDealerRole, IsDealerOwnerOrAdmin]
    pagination_class = CarPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("status",)
    search_fields = ("model__brand__name", "model__name", "description", "color")
    ordering_fields = ("created_at", "price", "year", "views_count")
    ordering = ("-created_at",)
    http_method_names = ("get", "post", "patch", "delete", "head", "options")
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_queryset(self):
        return (
            Car.objects.filter(dealer_id=self.request.user.dealer_id)
            .select_related("owner", "dealer", "dealer__city", "model", "model__brand", "city")
            .prefetch_related("images", "price_history")
        )

    def perform_create(self, serializer):
        user = self.request.user
        car_status = serializer.validated_data.get("status", Car.Status.ACTIVE)
        serializer.save(
            owner=user,
            dealer=user.dealer,
            published_at=timezone.now() if car_status == Car.Status.ACTIVE else None,
        )

    def perform_update(self, serializer):
        car = serializer.save()
        if car.status == Car.Status.ACTIVE and car.published_at is None:
            car.published_at = timezone.now()
            car.save(update_fields=("published_at", "updated_at"))

    def perform_destroy(self, instance):
        # Фото удаляются каскадом, файлы — из Cloudinary через сигнал post_delete
        instance.delete()

    # ── Фото ──

    @action(
        detail=True,
        methods=("post",),
        url_path="photos",
        parser_classes=(MultiPartParser, FormParser),
    )
    def upload_photos(self, request, pk=None):
        car = self.get_object()
        serializer = CarImagesUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = serializer.validated_data["images"]

        created = []
        with transaction.atomic():
            locked = Car.objects.select_for_update().get(pk=car.pk)
            if locked.images.count() + len(files) > MAX_IMAGES_PER_CAR:
                raise ValidationError(
                    {"images": f"У объявления может быть не более {MAX_IMAGES_PER_CAR} фотографий."}
                )
            last = locked.images.aggregate(m=Max("position"))["m"]
            next_pos = 0 if last is None else last + 1
            has_cover = locked.images.filter(is_cover=True).exists()
            for i, f in enumerate(files):
                created.append(
                    CarImage.objects.create(
                        car=locked,
                        image=f,
                        position=next_pos + i,
                        is_cover=not has_cover and i == 0,
                    )
                )
        return Response(
            CarImageSerializer(created, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def _get_photo(self, car, photo_id):
        return get_object_or_404(CarImage.objects.select_for_update(), pk=photo_id, car=car)

    @action(detail=True, methods=("delete",), url_path=r"photos/(?P<photo_id>\d+)")
    def delete_photo(self, request, pk=None, photo_id=None):
        car = self.get_object()
        with transaction.atomic():
            photo = self._get_photo(car, photo_id)
            was_cover = photo.is_cover
            photo.delete()  # файл удалится из Cloudinary после commit (signals.py)
            if was_cover:
                nxt = car.images.order_by("position", "pk").first()
                if nxt:
                    nxt.is_cover = True
                    nxt.save(update_fields=("is_cover", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=("post",), url_path=r"photos/(?P<photo_id>\d+)/main")
    def set_main_photo(self, request, pk=None, photo_id=None):
        car = self.get_object()
        with transaction.atomic():
            photo = self._get_photo(car, photo_id)
            car.images.filter(is_cover=True).exclude(pk=photo.pk).update(
                is_cover=False, updated_at=timezone.now()
            )
            photo.is_cover = True
            photo.save(update_fields=("is_cover", "updated_at"))
        return Response(CarImageSerializer(photo, context={"request": request}).data)


# ── Админ: салоны и менеджеры ──────────────────────────────────────────────

class AdminDealerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = DealerSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name", "slug", "phone")
    ordering = ("name",)
    pagination_class = None
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        return Dealer.objects.annotate(
            car_count=Count("cars", distinct=True),
            managers_count=Count("managers", filter=Q(managers__role="dealer"), distinct=True),
        ).select_related("city")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dealer = serializer.save()
        data = self.get_serializer(self.get_queryset().get(pk=dealer.pk)).data
        admin = serializer.created_admin
        data["admin"] = {"id": admin.id, "email": admin.email}
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        dealer = self.get_object()
        dealer.is_active = not dealer.is_active
        dealer.save(update_fields=("is_active", "updated_at"))
        return Response({"is_active": dealer.is_active})


class AdminManagerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = ManagerSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("dealer", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone", "dealer__name")
    ordering = ("email",)
    pagination_class = None
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        return User.objects.filter(role=User.Role.DEALER).select_related("dealer")

    def perform_update(self, serializer):
        user = serializer.save()
        if not user.is_active:
            revoke_user_refresh_tokens(user)

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = PasswordResetByAdminSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=("password", "updated_at"))
        revoke_user_refresh_tokens(user)
        return Response({"detail": "Пароль изменён. Передайте его менеджеру."})

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            user.delete()
        except ProtectedError:
            return Response(
                {"detail": "У менеджера есть объявления — удалить нельзя. Отключите аккаунт."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminDealerReviewViewSet(viewsets.ModelViewSet):
    """Модерация отзывов: публикация, отклонение, удаление."""

    permission_classes = [IsAdminRole]
    serializer_class = AdminDealerReviewSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_fields = ("status", "dealer")
    search_fields = ("author_name", "text", "dealer__name")
    ordering = ("-created_at",)
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get_queryset(self):
        return DealerReview.objects.select_related("dealer")
