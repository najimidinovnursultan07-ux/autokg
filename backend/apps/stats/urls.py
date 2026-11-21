from django.urls import path

from .views import DealerReportPdfView, DealerReportView

app_name = "stats"

urlpatterns = [
    path("dashboard/report/", DealerReportView.as_view(), name="dealer-report"),
    path("dashboard/report/pdf/", DealerReportPdfView.as_view(), name="dealer-report-pdf"),
]
