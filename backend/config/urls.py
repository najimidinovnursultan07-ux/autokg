from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.common.views import ApiRootView, ExchangeRatesView, HealthCheckView, ReadinessCheckView

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("django-admin/", admin.site.urls),
    path("api/health/", HealthCheckView.as_view(), name="health"),
    path("api/health/ready/", ReadinessCheckView.as_view(), name="readiness"),
    path("api/rates/", ExchangeRatesView.as_view(), name="rates"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/admin/", include("apps.admin_api.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/", include("apps.subscriptions.urls")),
    path("api/", include("apps.stats.urls")),
    path("api/", include("apps.ads.urls")),
    path("api/", include("apps.dealers.urls")),
    path("api/", include("apps.favorites.urls")),
    path("api/", include("apps.cars.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
