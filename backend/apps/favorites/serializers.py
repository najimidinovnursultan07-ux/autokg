from rest_framework import serializers

from apps.cars.models import Car
from apps.cars.serializers import PublicCarSerializer

from .models import Favorite


class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    car_details = PublicCarSerializer(source="car", read_only=True)
    car = serializers.PrimaryKeyRelatedField(
        queryset=Car.objects.filter(status=Car.Status.ACTIVE, dealer__is_active=True)
    )

    class Meta:
        model = Favorite
        fields = ("id", "user", "car", "car_details", "created_at")
        read_only_fields = ("id", "user", "created_at")

    def validate_car(self, car):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            if Favorite.objects.filter(user=request.user, car=car).exists():
                raise serializers.ValidationError(
                    "Это объявление уже добавлено в избранное."
                )
        return car
