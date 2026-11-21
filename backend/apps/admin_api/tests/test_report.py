from datetime import timedelta
from io import BytesIO

from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase
from apps.dealers.models import DealerReview
from apps.subscriptions.models import Plan
from apps.subscriptions.services import activate_subscription, use_promotion


class AdminReportTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        premium = Plan.objects.get(code="premium")
        activate_subscription(self.dealer_a, premium, 1, amount="7990", payment_method="cash")
        self.live = self.make_car(self.dealer_a, views_count=100, phone_views=7, whatsapp_clicks=3)
        expired = self.make_car(self.dealer_a)
        Car.objects.filter(pk=expired.pk).update(expires_at=timezone.now() - timedelta(days=1))
        self.make_car(self.dealer_a, status=Car.Status.SOLD)
        use_promotion(self.dealer_a, self.live, "top")
        DealerReview.objects.create(dealer=self.dealer_a, author_name="Аня", rating=4, text="Хороший салон, всё честно.", status="published")

    def test_report_rows_and_summary(self):
        resp = self.admin_client.get("/api/admin/report/")
        self.assertEqual(resp.status_code, 200)
        row = next(r for r in resp.data["rows"] if r["slug"] == "salon-a")
        self.assertEqual(row["plan"], "Премиум")
        self.assertFalse(row["is_trial"])
        self.assertEqual(row["cars_on_site"], 1)
        self.assertEqual(row["cars_expired"], 1)
        self.assertEqual(row["cars_sold"], 1)
        self.assertEqual(row["cars_added"], 3)
        self.assertEqual(row["views"], 100)
        self.assertEqual(row["contact_rate"], 10.0)
        self.assertEqual(row["promo_top"], 1)
        self.assertEqual(row["revenue"], "7990.00")
        self.assertEqual(row["rating"], 4.0)
        summary = resp.data["summary"]
        self.assertEqual(summary["dealers"], 2)
        self.assertEqual(summary["dealers_paid"], 1)
        self.assertEqual(summary["dealers_trial"], 1)
        self.assertEqual(summary["revenue"], "7990.00")
        self.assertEqual(resp.data["plans"], {"Премиум": 1, "Бизнес (пробный)": 1})

    def test_period_filter_excludes_old_revenue(self):
        resp = self.admin_client.get("/api/admin/report/?from=2020-01-01&to=2020-01-31")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["summary"]["revenue"], "0.00")
        self.assertEqual(resp.data["summary"]["cars_added"], 0)
        self.assertEqual(resp.data["summary"]["views"], 100)  # счётчики — за всё время
        self.assertEqual(self.admin_client.get("/api/admin/report/?from=bad").status_code, 400)

    def test_export_xlsx(self):
        resp = self.admin_client.get("/api/admin/report/export/")
        self.assertEqual(resp.status_code, 200)
        wb = load_workbook(BytesIO(resp.content))
        self.assertEqual(wb.sheetnames, ["Сводка", "Салоны"])
        names = [c.value for c in wb["Салоны"]["A"]][1:]
        self.assertEqual(sorted(names), ["Салон А", "Салон Б"])

    def test_export_pdf(self):
        resp = self.admin_client.get("/api/admin/report/pdf/?from=2026-01-01&to=2026-12-31")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))
        self.assertIn("2026-01-01_2026-12-31.pdf", resp["Content-Disposition"])

    def test_dealer_cannot_see_report(self):
        client = APIClient()
        client.force_authenticate(self.manager_a)
        self.assertEqual(client.get("/api/admin/report/").status_code, 403)
        self.assertEqual(client.get("/api/admin/report/export/").status_code, 403)
        self.assertEqual(client.get("/api/admin/report/pdf/").status_code, 403)
