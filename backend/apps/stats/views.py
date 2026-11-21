from django.db import transaction
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dealers.models import Dealer
from apps.dealers.permissions import IsDealerRole

from .models import PDF_DOWNLOADS_PER_MONTH, ReportDownload
from .pdf import build_dealer_report_pdf
from .report import build_dealer_report, downloads_left, parse_month


class DealerReportView(APIView):
    """Отчёт салона за месяц: ?month=ГГГГ-ММ (по умолчанию текущий)."""

    permission_classes = [IsDealerRole]

    def get(self, request):
        month = parse_month(request.query_params.get("month"))
        return Response(build_dealer_report(request.user.dealer, month))


class DealerReportPdfView(APIView):
    """PDF отчёта. Не больше PDF_DOWNLOADS_PER_MONTH скачиваний в календарный месяц на салон."""

    permission_classes = [IsDealerRole]

    def get(self, request):
        month = parse_month(request.query_params.get("month"))
        dealer = request.user.dealer
        with transaction.atomic():
            Dealer.objects.select_for_update().get(pk=dealer.pk)  # два клика одновременно не обойдут лимит
            left, _ = downloads_left(dealer)
            if left <= 0:
                return Response(
                    {"detail": f"PDF можно скачать не больше {PDF_DOWNLOADS_PER_MONTH} раз в месяц. "
                               "Лимит обновится 1-го числа."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            content = build_dealer_report_pdf(build_dealer_report(dealer, month))
            ReportDownload.objects.create(dealer=dealer, user=request.user, report_month=month)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="autobuy-otchet-{month:%Y-%m}.pdf"'
        response["X-Downloads-Left"] = str(left - 1)
        response["Access-Control-Expose-Headers"] = "Content-Disposition, X-Downloads-Left"
        return response
