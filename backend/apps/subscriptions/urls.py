from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminPlanRequestViewSet,
    AdminPlanViewSet,
    AdminSubscriptionViewSet,
    MySubscriptionView,
    PlanListView,
    PlanRequestCreateView,
    PromoteView,
    StatsExportView,
    SubscriptionRemindersView,
)

app_name = "subscriptions"

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("admin/plans", AdminPlanViewSet, basename="admin-plan")
router.register("admin/subscriptions", AdminSubscriptionViewSet, basename="admin-subscription")
router.register("admin/plan-requests", AdminPlanRequestViewSet, basename="admin-plan-request")

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plans"),
    path("dashboard/subscription/", MySubscriptionView.as_view(), name="my-subscription"),
    path("dashboard/subscription/requests/", PlanRequestCreateView.as_view(), name="plan-request"),
    path("dashboard/promote/", PromoteView.as_view(), name="promote"),
    path("dashboard/stats-export/", StatsExportView.as_view(), name="stats-export"),
    path("internal/subscription-reminders/", SubscriptionRemindersView.as_view(), name="reminders"),
    path("", include(router.urls)),
]
