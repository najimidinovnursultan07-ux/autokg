from django.urls import path

from .views import AdClickView, AdImpressionsView, AdListView


app_name = "ads"

urlpatterns = [
    path("ads/", AdListView.as_view(), name="list"),
    path("ads/impressions/", AdImpressionsView.as_view(), name="impressions"),
    path("ads/<int:pk>/click/", AdClickView.as_view(), name="click"),
]
