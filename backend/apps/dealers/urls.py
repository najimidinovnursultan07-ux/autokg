from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    AdminDealerViewSet,
    AdminManagerViewSet,
    AdminStatsView,
    DealerCarsView,
    DealerProfileView,
    PublicDealerDetailView,
    PublicDealerListView,
)

router = DefaultRouter()
router.register("admin/dealers", AdminDealerViewSet, basename="admin-dealer")
router.register("admin/managers", AdminManagerViewSet, basename="admin-manager")

app_name = "dealers"

urlpatterns = [
    # Публичные
    path("dealers/", PublicDealerListView.as_view(), name="dealer-list"),
    path("dealers/<slug:slug>/", PublicDealerDetailView.as_view(), name="dealer-detail"),
    # Кабинет дилера
    path("dashboard/dealer/", DealerProfileView.as_view(), name="dealer-profile"),
    path("dashboard/cars/", DealerCarsView.as_view(), name="dealer-cars"),
    # Админ stats
    path("admin/dealer-stats/", AdminStatsView.as_view(), name="dealer-stats"),
    # Admin CRUD (router)
    path("", include(router.urls)),
]
