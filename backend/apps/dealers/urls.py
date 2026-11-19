from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminDealerViewSet,
    AdminManagerViewSet,
    DashboardCarViewSet,
    DealerProfileView,
    PublicDealerDetailView,
    PublicDealerListView,
)

app_name = "dealers"

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("admin/dealers", AdminDealerViewSet, basename="admin-dealer")
router.register("admin/managers", AdminManagerViewSet, basename="admin-manager")
router.register("dashboard/cars", DashboardCarViewSet, basename="dashboard-car")

urlpatterns = [
    # Публичные
    path("dealers/", PublicDealerListView.as_view(), name="dealer-list"),
    path("dealers/<str:slug>/", PublicDealerDetailView.as_view(), name="dealer-detail"),
    # Кабинет салона
    path("dashboard/dealer/", DealerProfileView.as_view(), name="dealer-profile"),
    path("", include(router.urls)),
]
