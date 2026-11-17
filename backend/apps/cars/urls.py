from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BrandViewSet, CarViewSet, CityViewSet, ModelViewSet


app_name = "cars"

router = DefaultRouter()
router.register("brands", BrandViewSet, basename="brand")
router.register("models", ModelViewSet, basename="model")
router.register("cities", CityViewSet, basename="city")
router.register("cars", CarViewSet, basename="car")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "my-cars/",
        CarViewSet.as_view({"get": "my_cars"}),
        name="my-cars",
    ),
]
