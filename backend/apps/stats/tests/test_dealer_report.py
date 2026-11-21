from datetime import date, timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase
from apps.stats.models import CarMonthStat, DealerMonthStat, ReportDownload
from apps.stats.services import month_of, purge_old_stats, shift_month
from apps.subscriptions.models import Plan
from apps.subscriptions.services import activate_subscription


class DealerReportTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        self.anon = APIClient()
        self.month = month_of()

    def test_views_contacts_added_and_sold_are_counted_by_month(self):
        car = self.make_car(self.dealer_a)
        self.anon.get(f"/api/cars/{car.pk}/")
        self.anon.get(f"/api/cars/{car.pk}/")
        self.anon.post(f"/api/cars/{car.pk}/contacts/", {"kind": "phone"}, format="json")
        self.anon.post(f"/api/cars/{car.pk}/contacts/", {"kind": "whatsapp"}, format="json")
        self.client_a.get(f"/api/cars/{car.pk}/")  # свой просмотр не считается
        resp = self.client_a.patch(f"/api/dashboard/cars/{car.pk}/", {"status": "sold"}, format="json")
        self.assertEqual(resp.status_code, 200)
        car.refresh_from_db()
        self.assertIsNotNone(car.sold_at)

        stat = DealerMonthStat.objects.get(dealer=self.dealer_a, month=self.month)
        self.assertEqual((stat.cars_added, stat.cars_sold, stat.views, stat.phone_views, stat.whatsapp_clicks), (1, 1, 2, 1, 1))

        report = self.client_a.get("/api/dashboard/report/").data
        self.assertEqual(report["current"]["cars_sold"], 1)
        self.assertEqual(report["current"]["contact_rate"], 100.0)
        self.assertEqual(report["listings"]["sold"], 1)
        self.assertEqual(len(report["sold"]), 1)
        self.assertEqual(report["top_cars"][0]["views"], 2)
        self.assertEqual(len(report["months"]), 12)

        # отмена продажи убирает её из месяца
        self.client_a.patch(f"/api/dashboard/cars/{car.pk}/", {"status": "active"}, format="json")
        self.assertEqual(DealerMonthStat.objects.get(dealer=self.dealer_a, month=self.month).cars_sold, 0)

    def test_start_plan_hides_contacts(self):
        activate_subscription(self.dealer_a, Plan.objects.get(code="start"), 1)
        car = self.make_car(self.dealer_a)
        self.anon.get(f"/api/cars/{car.pk}/")
        report = self.client_a.get("/api/dashboard/report/").data
        self.assertFalse(report["show_contacts"])
        self.assertIsNone(report["current"]["phone_views"])
        self.assertIsNone(report["top_cars"][0]["phone_views"])

    def test_month_param_limited_to_12_months(self):
        old = shift_month(self.month, -12).strftime("%Y-%m")
        self.assertEqual(self.client_a.get(f"/api/dashboard/report/?month={old}").status_code, 400)
        ok = shift_month(self.month, -11).strftime("%Y-%m")
        self.assertEqual(self.client_a.get(f"/api/dashboard/report/?month={ok}").status_code, 200)
        self.assertEqual(self.client_a.get("/api/dashboard/report/?month=abc").status_code, 400)

    def test_pdf_only_twice_a_month(self):
        self.make_car(self.dealer_a, status=Car.Status.SOLD)
        for left in (1, 0):
            resp = self.client_a.get("/api/dashboard/report/pdf/")
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.content.startswith(b"%PDF"))
            self.assertEqual(resp["X-Downloads-Left"], str(left))
        resp = self.client_a.get("/api/dashboard/report/pdf/")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("2 раз", resp.data["detail"])
        self.assertEqual(self.client_a.get("/api/dashboard/report/").data["downloads"]["left"], 0)
        # у другого салона свой лимит
        client_b = APIClient()
        client_b.force_authenticate(self.manager_b)
        self.assertEqual(client_b.get("/api/dashboard/report/pdf/").status_code, 200)
        # скачивания прошлого месяца не считаются
        ReportDownload.objects.filter(dealer=self.dealer_a).update(created_at=timezone.now() - timedelta(days=40))
        self.assertEqual(self.client_a.get("/api/dashboard/report/pdf/").status_code, 200)

    def test_purge_removes_data_older_than_12_months(self):
        old = shift_month(self.month, -12)
        kept = shift_month(self.month, -11)
        DealerMonthStat.objects.create(dealer=self.dealer_a, month=old, views=5)
        DealerMonthStat.objects.create(dealer=self.dealer_a, month=kept, views=7)
        CarMonthStat.objects.create(dealer=self.dealer_a, car_title="x", month=old, views=1)
        self.assertEqual(purge_old_stats(), 2)
        self.assertEqual(list(DealerMonthStat.objects.values_list("month", flat=True)), [kept])

    def test_other_dealer_and_admin_cannot_use_dealer_report(self):
        self.assertEqual(self.anon.get("/api/dashboard/report/").status_code, 401)
        admin = APIClient()
        admin.force_authenticate(self.admin)
        self.assertEqual(admin.get("/api/dashboard/report/").status_code, 403)

    def test_month_helpers(self):
        self.assertEqual(shift_month(date(2026, 1, 1), -1), date(2025, 12, 1))
        self.assertEqual(shift_month(date(2026, 11, 1), 2), date(2027, 1, 1))
