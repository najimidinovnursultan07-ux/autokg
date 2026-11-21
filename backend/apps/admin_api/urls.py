from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminBrandViewSet,
    AdminCarViewSet,
    AdminCityViewSet,
    AdminModelViewSet,
    AdminReportExportView,
    AdminReportView,
    AdminStatsView,
    AdminUserViewSet,
)


app_name = "admin_api"

router = DefaultRouter()
router.register("users", AdminUserViewSet, basename="admin-user")
router.register("cars", AdminCarViewSet, basename="admin-car")
router.register("brands", AdminBrandViewSet, basename="admin-brand")
router.register("models", AdminModelViewSet, basename="admin-model")
router.register("cities", AdminCityViewSet, basename="admin-city")

urlpatterns = [
    path("stats/", AdminStatsView.as_view(), name="stats"),
    path("report/", AdminReportView.as_view(), name="report"),
    path("report/export/", AdminReportExportView.as_view(), name="report-export"),
    path("", include(router.urls)),
]
