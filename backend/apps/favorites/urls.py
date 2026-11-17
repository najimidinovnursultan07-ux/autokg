from rest_framework.routers import DefaultRouter

from .views import FavoriteViewSet


app_name = "favorites"

router = DefaultRouter()
router.register("favorites", FavoriteViewSet, basename="favorite")

urlpatterns = router.urls
