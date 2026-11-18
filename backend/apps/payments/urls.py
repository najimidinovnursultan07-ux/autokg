from django.urls import path
from .views import (
    CarPromotionsView,
    CreatePaymentView,
    MockPaymentView,
    PaymentHistoryView,
    ServicePricesView,
    WebhookView,
)

app_name = "payments"

urlpatterns = [
    path("prices/", ServicePricesView.as_view(), name="prices"),
    path("create/", CreatePaymentView.as_view(), name="create"),
    path("mock/", MockPaymentView.as_view(), name="mock"),
    path("history/", PaymentHistoryView.as_view(), name="history"),
    path("webhook/", WebhookView.as_view(), name="webhook"),
    path("car/<uuid:car_id>/promotions/", CarPromotionsView.as_view(), name="car-promotions"),
]
