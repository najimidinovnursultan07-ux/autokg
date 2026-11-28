from django.urls import path

from .views import AlertsRunView, PriceWatchCreateView, SavedSearchCreateView, TelegramWebhookView

urlpatterns = [
    path("alerts/searches/", SavedSearchCreateView.as_view(), name="alerts-search-create"),
    path("alerts/watches/", PriceWatchCreateView.as_view(), name="alerts-watch-create"),
    path("alerts/telegram/webhook/", TelegramWebhookView.as_view(), name="alerts-telegram-webhook"),
    path("internal/alerts/run/", AlertsRunView.as_view(), name="alerts-run"),
]
