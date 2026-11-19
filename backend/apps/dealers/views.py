from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets, mixins
from rest_framework.decorators import action

from apps.cars.models import Car
from apps.cars.serializers import CarSerializer
from .models import Dealer
from .permissions import IsAdminRole, IsDealerRole, IsDealerOrAdmin
from .serializers import (
    DealerPublicSerializer,
    DealerSerializer,
    DealerProfileSerializer,
)


# ── Публичные ──────────────────────────────────────────────────────────────

class PublicDealerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        dealers = Dealer.objects.filter(is_active=True).annotate(
            car_count=Count("cars", filter=__import__("django.db.models", fromlist=["Q"]).Q(
                cars__status="published"
            ))
        ).select_related("city")
        return Response(DealerPublicSerializer(dealers, many=True).data)


class PublicDealerDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        dealer = get_object_or_404(
            Dealer.objects.annotate(car_count=Count("cars")).select_related("city"),
            slug=slug,
            is_active=True,
        )
        cars = Car.objects.filter(
            dealer=dealer,
            status="published",
        ).select_related("model", "model__brand", "city").prefetch_related("images")

        return Response({
            "dealer": DealerPublicSerializer(dealer).data,
            "cars": CarSerializer(cars, many=True, context={"request": request}).data,
        })


# ── Кабинет дилера ─────────────────────────────────────────────────────────

class DealerProfileView(APIView):
    permission_classes = [IsDealerRole]

    def get(self, request):
        return Response(DealerProfileSerializer(request.user.dealer).data)

    def patch(self, request):
        serializer = DealerProfileSerializer(
            request.user.dealer,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DealerCarsView(APIView):
    """Список машин своего салона (для дилера)."""
    permission_classes = [IsDealerRole]

    def get(self, request):
        cars = Car.objects.filter(
            dealer=request.user.dealer,
        ).select_related("model", "model__brand", "city").prefetch_related("images")
        return Response(CarSerializer(cars, many=True, context={"request": request}).data)


# ── Админ ──────────────────────────────────────────────────────────────────

class AdminDealerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = DealerSerializer
    queryset = Dealer.objects.annotate(car_count=Count("cars")).select_related("city")
    lookup_field = "id"

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, id=None):
        dealer = self.get_object()
        dealer.is_active = not dealer.is_active
        dealer.save(update_fields=("is_active", "updated_at"))
        return Response({"is_active": dealer.is_active})


class AdminManagerViewSet(viewsets.ViewSet):
    """Создание и управление менеджерами (dealers)."""
    permission_classes = [IsAdminRole]

    def list(self, request):
        from apps.accounts.models import User
        from apps.accounts.serializers import UserSerializer
        managers = User.objects.filter(role="dealer").select_related("dealer")
        from rest_framework import serializers as drf_serializers

        class ManagerSerializer(drf_serializers.ModelSerializer):
            dealer_name = drf_serializers.CharField(source="dealer.name", read_only=True, default="")
            dealer_slug = drf_serializers.CharField(source="dealer.slug", read_only=True, default="")
            class Meta:
                model = User
                fields = ("id", "email", "first_name", "last_name", "is_active", "dealer_id", "dealer_name", "dealer_slug")

        return Response(ManagerSerializer(managers, many=True).data)

    def create(self, request):
        from apps.accounts.models import User
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")
        first_name = request.data.get("first_name", "")
        last_name = request.data.get("last_name", "")
        dealer_id = request.data.get("dealer_id")

        if not email or not password:
            return Response({"detail": "Email и пароль обязательны."}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"detail": "Пользователь с таким email уже существует."}, status=400)

        dealer = None
        if dealer_id:
            dealer = get_object_or_404(Dealer, pk=dealer_id)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role="dealer",
            dealer=dealer,
        )
        return Response({"id": user.id, "email": user.email, "dealer_id": dealer_id}, status=201)

    def partial_update(self, request, pk=None):
        from apps.accounts.models import User
        user = get_object_or_404(User, pk=pk, role="dealer")
        dealer_id = request.data.get("dealer_id")
        if dealer_id is not None:
            dealer = get_object_or_404(Dealer, pk=dealer_id)
            user.dealer = dealer
        if "is_active" in request.data:
            user.is_active = bool(request.data["is_active"])
        if "password" in request.data and request.data["password"]:
            user.set_password(request.data["password"])
        user.save()
        return Response({"detail": "Обновлено."})

    def destroy(self, request, pk=None):
        from apps.accounts.models import User
        user = get_object_or_404(User, pk=pk, role="dealer")
        user.is_active = False
        user.save(update_fields=("is_active",))
        return Response(status=204)


class AdminStatsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        from apps.accounts.models import User
        total_dealers = Dealer.objects.count()
        active_dealers = Dealer.objects.filter(is_active=True).count()
        total_cars = Car.objects.count()
        published_cars = Car.objects.filter(status="published").count()
        total_managers = User.objects.filter(role="dealer").count()

        by_dealer = list(
            Car.objects.values("dealer__name", "dealer__slug")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        return Response({
            "dealers": {"total": total_dealers, "active": active_dealers},
            "cars": {"total": total_cars, "published": published_cars},
            "managers": {"total": total_managers},
            "cars_by_dealer": by_dealer,
        })
