from django.db import transaction
from django.db.models import F, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.moderation.models import ModerationEvent
from apps.common.permissions import IsAutoKGAdmin

from .filters import CarFilter
from .models import Brand, Car, CarImage, City, Model
from .pagination import CarPagination
from .permissions import CarPermission
from .serializers import (
    CarImageSerializer,
    CarImageReorderSerializer,
    CarImageUpdateSerializer,
    CarImagesUploadSerializer,
    CarSerializer,
    BrandSerializer,
    CitySerializer,
    ModelSerializer,
    RejectCarSerializer,
)


MAX_IMAGES_PER_CAR = 20


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


class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    pagination_class = CarPagination
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = CarFilter
    search_fields = (
        "model__brand__name",
        "model__name",
        "city__name",
        "description",
    )
    ordering_fields = (
        "price",
        "published_at",
        "created_at",
        "year",
        "mileage",
    )
    ordering = ("-published_at", "-created_at")
    lookup_value_regex = "[0-9a-f-]{36}"

    def get_permissions(self):
        if self.action in {"approve", "reject", "moderation_queue"}:
            permission_classes = (IsAutoKGAdmin,)
        elif self.action == "my_cars":
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (CarPermission,)
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = Car.objects.select_related(
            "owner",
            "model",
            "model__brand",
            "city",
        ).prefetch_related("images")
        user = self.request.user
        is_admin = (
            user.is_authenticated
            and user.is_staff
            and getattr(user, "role", None) == "admin"
        )

        if self.action == "moderation_queue" and is_admin:
            return queryset.filter(status=Car.Status.PENDING)
        if self.action in {"approve", "reject"} and is_admin:
            return queryset
        if self.action == "list":
            from django.utils import timezone
            from apps.payments.models import Promotion
            from django.db.models import BooleanField, ExpressionWrapper, Exists, OuterRef
            active_top = Promotion.objects.filter(
                car=OuterRef("pk"),
                promotion_type="top",
                is_active=True,
                expires_at__gt=timezone.now(),
            )
            return queryset.filter(status=Car.Status.PUBLISHED).annotate(
                has_top=ExpressionWrapper(Exists(active_top), output_field=BooleanField())
            ).order_by("-has_top", "-published_at", "-created_at")
        if self.action == "retrieve" or (
            self.action == "upload_images" and self.request.method == "GET"
        ):
            if user.is_authenticated:
                return queryset.filter(
                    Q(status=Car.Status.PUBLISHED)
                    | (Q(owner=user) & ~Q(status=Car.Status.REMOVED))
                )
            return queryset.filter(status=Car.Status.PUBLISHED)
        if self.action == "my_cars":
            return queryset.filter(owner=user).exclude(status=Car.Status.REMOVED)
        if user.is_authenticated:
            if is_admin:
                return queryset
            return queryset.filter(owner=user).exclude(status=Car.Status.REMOVED)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "upload_images":
            if self.request.method == "GET":
                return CarImageSerializer
            return CarImagesUploadSerializer
        if self.action == "reorder_images":
            return CarImageReorderSerializer
        if self.action == "reject":
            return RejectCarSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _mark_published_listing_pending(self, car):
        if car.status == Car.Status.PUBLISHED:
            car.status = Car.Status.PENDING
            car.save(update_fields=("status", "updated_at"))
            ModerationEvent.objects.create(
                car=car,
                actor=self.request.user,
                action=ModerationEvent.Action.SUBMITTED,
                reason="Повторная модерация после изменения объявления.",
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            car = serializer.save()
            self._mark_published_listing_pending(car)

    def _transition(
        self,
        car,
        *,
        allowed_statuses,
        new_status,
        event_action,
        reason="",
        publish=False,
        require_image=False,
    ):
        with transaction.atomic():
            car = Car.objects.select_for_update().get(pk=car.pk)
            if car.status not in allowed_statuses:
                raise ValidationError(
                    {"status": f"Нельзя выполнить действие для статуса «{car.status}»."}
                )
            if require_image and not car.images.exists():
                raise ValidationError(
                    {"images": "Добавьте хотя бы одну фотографию перед публикацией."}
                )

            car.status = new_status
            update_fields = ["status", "updated_at"]
            if publish:
                car.published_at = timezone.now()
                update_fields.append("published_at")
            car.save(update_fields=update_fields)
            ModerationEvent.objects.create(
                car=car,
                actor=self.request.user,
                action=event_action,
                reason=reason,
            )
        return car

    def _submit_for_moderation(self, request, car, allowed_statuses):
        car = self._transition(
            car,
            allowed_statuses=allowed_statuses,
            new_status=Car.Status.PENDING,
            event_action=ModerationEvent.Action.SUBMITTED,
            require_image=True,
        )
        return Response(
            self.get_serializer(car).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        car = self.get_object()
        if car.status != Car.Status.REMOVED:
            self._transition(
                car,
                allowed_statuses=Car.Status.values,
                new_status=Car.Status.REMOVED,
                event_action=ModerationEvent.Action.REMOVED,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Өз машинасын же adminдин карашы санга кирбесин
        if instance.status == Car.Status.PUBLISHED and (
            not request.user.is_authenticated or request.user.pk != instance.owner_id
        ):
            Car.objects.filter(pk=instance.pk).update(views_count=F("views_count") + 1)
            instance.views_count = (instance.views_count or 0) + 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=("get",), url_path="my-cars")
    def my_cars(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @action(
        detail=False,
        methods=("get",),
        url_path="moderation-queue",
        permission_classes=(IsAutoKGAdmin,),
    )
    def moderation_queue(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @action(detail=True, methods=("post",))
    def submit(self, request, *args, **kwargs):
        car = self.get_object()
        return self._submit_for_moderation(
            request,
            car,
            (Car.Status.DRAFT, Car.Status.REJECTED, Car.Status.INACTIVE),
        )

    @action(detail=True, methods=("post",))
    def reactivate(self, request, *args, **kwargs):
        car = self.get_object()
        return self._submit_for_moderation(
            request,
            car,
            (Car.Status.INACTIVE,),
        )

    @action(detail=True, methods=("post",))
    def deactivate(self, request, *args, **kwargs):
        car = self._transition(
            self.get_object(),
            allowed_statuses=(Car.Status.PUBLISHED,),
            new_status=Car.Status.INACTIVE,
            event_action=ModerationEvent.Action.DEACTIVATED,
        )
        return Response(self.get_serializer(car).data)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(IsAutoKGAdmin,),
    )
    def approve(self, request, *args, **kwargs):
        car = self._transition(
            self.get_object(),
            allowed_statuses=(Car.Status.PENDING,),
            new_status=Car.Status.PUBLISHED,
            event_action=ModerationEvent.Action.APPROVED,
            publish=True,
            require_image=True,
        )
        return Response(self.get_serializer(car).data)

    @action(
        detail=True,
        methods=("post",),
        permission_classes=(IsAutoKGAdmin,),
    )
    def reject(self, request, *args, **kwargs):
        serializer = RejectCarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = self._transition(
            self.get_object(),
            allowed_statuses=(Car.Status.PENDING,),
            new_status=Car.Status.REJECTED,
            event_action=ModerationEvent.Action.REJECTED,
            reason=serializer.validated_data["reason"],
        )
        return Response(CarSerializer(car, context=self.get_serializer_context()).data)

    @action(
        detail=True,
        methods=("get", "post"),
        parser_classes=(MultiPartParser, FormParser),
        url_path="images",
    )
    def upload_images(self, request, *args, **kwargs):
        car = self.get_object()
        if request.method == "GET":
            return Response(
                CarImageSerializer(
                    car.images.all(),
                    many=True,
                    context=self.get_serializer_context(),
                ).data
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded_images = serializer.validated_data["images"]
        created_images = []

        with transaction.atomic():
            locked_car = Car.objects.select_for_update().get(pk=car.pk)
            current_count = locked_car.images.count()
            if current_count + len(uploaded_images) > MAX_IMAGES_PER_CAR:
                raise ValidationError(
                    {"images": f"У объявления может быть не более {MAX_IMAGES_PER_CAR} фотографий."}
                )

            last_position = locked_car.images.aggregate(
                last_position=Max("position")
            )["last_position"]
            next_position = (last_position + 1) if last_position is not None else 0
            has_cover = locked_car.images.filter(is_cover=True).exists()

            for index, image in enumerate(uploaded_images):
                car_image = CarImage(
                    car=locked_car,
                    image=image,
                    position=next_position + index,
                    is_cover=not has_cover and index == 0,
                )
                car_image.save()
                created_images.append(car_image)
            self._mark_published_listing_pending(locked_car)

        return Response(
            CarImageSerializer(
                created_images,
                many=True,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=("patch", "delete"),
        url_path=r"images/(?P<image_id>\d+)",
    )
    def image_detail(self, request, *args, **kwargs):
        car = self.get_object()
        with transaction.atomic():
            locked_car = Car.objects.select_for_update().get(pk=car.pk)
            image = get_object_or_404(
                CarImage.objects.select_for_update(),
                pk=kwargs["image_id"],
                car=locked_car,
            )

            if request.method == "PATCH":
                serializer = CarImageUpdateSerializer(
                    data=request.data,
                    partial=True,
                )
                serializer.is_valid(raise_exception=True)
                make_cover = serializer.validated_data.get("is_cover")
                if make_cover is True:
                    locked_car.images.filter(is_cover=True).exclude(
                        pk=image.pk
                    ).update(is_cover=False, updated_at=timezone.now())
                    image.is_cover = True
                    image.save(update_fields=("is_cover", "updated_at"))
                elif make_cover is False and image.is_cover:
                    image.is_cover = False
                    image.save(update_fields=("is_cover", "updated_at"))
                    next_image = locked_car.images.order_by("position", "pk").first()
                    if next_image is not None:
                        next_image.is_cover = True
                        next_image.save(update_fields=("is_cover", "updated_at"))
                self._mark_published_listing_pending(locked_car)
                response_data = CarImageSerializer(
                    image,
                    context=self.get_serializer_context(),
                ).data
                return Response(response_data)

            storage = image.image.storage
            image_name = image.image.name
            was_cover = image.is_cover
            image.delete()
            if was_cover:
                next_image = locked_car.images.order_by("position", "pk").first()
                if next_image is not None:
                    next_image.is_cover = True
                    next_image.save(update_fields=("is_cover", "updated_at"))
            self._mark_published_listing_pending(locked_car)
            transaction.on_commit(lambda: storage.delete(image_name))

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=("post",),
        url_path="images/reorder",
    )
    def reorder_images(self, request, *args, **kwargs):
        car = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_ids = serializer.validated_data["image_ids"]

        with transaction.atomic():
            locked_car = Car.objects.select_for_update().get(pk=car.pk)
            images = list(
                CarImage.objects.select_for_update()
                .filter(car=locked_car)
                .order_by("position", "pk")
            )
            existing_ids = {image.pk for image in images}
            if set(requested_ids) != existing_ids:
                raise ValidationError(
                    {
                        "image_ids": (
                            "Передайте все идентификаторы фотографий этого "
                            "объявления ровно по одному."
                        )
                    }
                )

            current_max = max(image.position for image in images)
            temporary_offset = current_max + len(images) + 1
            CarImage.objects.filter(car=locked_car).update(
                position=F("position") + temporary_offset
            )
            images_by_id = {image.pk: image for image in images}
            updated_at = timezone.now()
            ordered_images = []
            for position, image_id in enumerate(requested_ids):
                image = images_by_id[image_id]
                image.position = position
                image.updated_at = updated_at
                ordered_images.append(image)
            CarImage.objects.bulk_update(
                ordered_images,
                fields=("position", "updated_at"),
            )
            self._mark_published_listing_pending(locked_car)

        return Response(
            CarImageSerializer(
                ordered_images,
                many=True,
                context=self.get_serializer_context(),
            ).data
        )
