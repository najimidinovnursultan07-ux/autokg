from datetime import timedelta
from io import BytesIO, StringIO
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase
from apps.dealers.importer import COLUMNS
from apps.subscriptions.models import Plan, PlanRequest, Subscription
from apps.subscriptions.notifications import send_subscription_reminders
from apps.subscriptions.services import activate_subscription

HEADERS = [f"{title} *" if required else title for _, title, required, _ in COLUMNS]


def xlsx(rows, headers=HEADERS, name="cars.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buffer = BytesIO()
    wb.save(buffer)
    return SimpleUploadedFile(
        name, buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def row(**overrides):
    data = {
        "brand": "Toyota", "model": "Camry", "year": 2019, "price": "1 850 000", "currency": "сом",
        "mileage": 85000, "engine_volume": 2.5, "engine_type": "Бензин", "transmission": "Автоматическая",
        "drive_type": "Передний", "body_type": "Седан", "condition": "С пробегом", "color": "белый",
        "city": "бишкек", "contact_phone": "", "description": "Хорошее состояние",
        "duration_days": "",
    }
    data.update(overrides)
    return [data[field] for field, _, _, _ in COLUMNS]


class ExcelImportTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        self.start = Plan.objects.get(code="start")

    def upload(self, file, publish=False):
        return self.client_a.post(
            "/api/dashboard/cars/import/", {"file": file, "publish": "1" if publish else "0"}, format="multipart"
        )

    def test_template_has_headers_and_reference(self):
        resp = self.client_a.get("/api/dashboard/cars/import-template/")
        self.assertEqual(resp.status_code, 200)
        wb = load_workbook(BytesIO(resp.content))
        self.assertEqual([c.value for c in wb["Объявления"][1]], HEADERS)
        self.assertIn("Справочник", wb.sheetnames)

    def test_import_creates_hidden_cars_by_default(self):
        resp = self.upload(xlsx([row(), row(year=2020, currency="$", price=15000)]))
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data, {"created": 2, "published": 0, "hidden": 2})
        cars = Car.objects.filter(dealer=self.dealer_a).order_by("year")
        self.assertEqual([c.status for c in cars], ["hidden", "hidden"])
        self.assertEqual(str(cars[0].price), "1850000.00")
        self.assertEqual(cars[1].currency, "USD")
        self.assertEqual(cars[0].contact_phone, "+996700111111")  # телефон салона
        self.assertIsNotNone(cars[0].expires_at)  # по умолчанию 30 дней

    def test_import_duration_column(self):
        resp = self.upload(xlsx([row(duration_days=7), row(year=2020, duration_days="без срока")]))
        self.assertEqual(resp.status_code, 201, resp.data)
        cars = Car.objects.filter(dealer=self.dealer_a).order_by("year")
        self.assertEqual((cars[0].expires_at - cars[0].created_at).days, 6)
        self.assertIsNone(cars[1].expires_at)
        resp = self.upload(xlsx([row(duration_days=5)]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Срок размещения", " ".join(resp.data["errors"]))

    def test_publish_respects_plan_limit(self):
        # пробный «Бизнес», лимит 30
        for _ in range(29):
            self.make_car(self.dealer_a)
        resp = self.upload(xlsx([row(), row(), row()]), publish=True)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data, {"created": 3, "published": 1, "hidden": 2})
        self.assertEqual(Car.objects.filter(dealer=self.dealer_a, status="active").count(), 30)

    def test_errors_listed_by_row_and_nothing_created(self):
        resp = self.upload(xlsx([row(), row(model="Нет такой"), row(engine_type="Пар", year=1700)]))
        self.assertEqual(resp.status_code, 400)
        errors = " | ".join(resp.data["errors"])
        self.assertIn("Строка 3", errors)
        self.assertIn("Модели «Нет такой»", errors)
        self.assertIn("Строка 4", errors)
        self.assertIn("Топливо", errors)
        self.assertIn("Год", errors)
        self.assertEqual(Car.objects.filter(dealer=self.dealer_a).count(), 0)

    def test_wrong_headers_or_format(self):
        resp = self.upload(xlsx([["x"]], headers=["Что-то"]))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Марка", resp.data["detail"])
        bad = SimpleUploadedFile("cars.csv", b"a;b", content_type="text/csv")
        self.assertEqual(self.upload(bad).status_code, 400)

    def test_start_plan_has_no_excel_import(self):
        activate_subscription(self.dealer_a, self.start, 1)
        self.assertEqual(self.client_a.get("/api/dashboard/cars/import-template/").status_code, 403)
        self.assertEqual(self.upload(xlsx([row()])).status_code, 403)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    TELEGRAM_BOT_TOKEN="token", TELEGRAM_ADMIN_CHAT_ID="42", CRON_SECRET="s3cret",
    FRONTEND_URL="https://autobuy.test",
)
class ReminderTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.business = Plan.objects.get(code="business")
        telegram = patch("apps.subscriptions.notifications.send_telegram", return_value=True)
        self.telegram = telegram.start()
        self.addCleanup(telegram.stop)

    def set_expiry(self, dealer, delta):
        now = timezone.now()
        Subscription.objects.filter(dealer=dealer).update(
            starts_at=now + delta - timedelta(days=30), expires_at=now + delta
        )

    def test_three_days_then_one_day_then_expired(self):
        self.set_expiry(self.dealer_b, timedelta(days=20))  # у Б всё хорошо
        self.set_expiry(self.dealer_a, timedelta(days=2, hours=12))
        result = send_subscription_reminders()
        self.assertEqual(result["expiring"], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["a@test.kg"])
        self.assertIn("через 3 дн.", mail.outbox[0].subject)
        self.assertIn("https://autobuy.test/dashboard/subscription", mail.outbox[0].body)
        self.assertIn("Салон А", self.telegram.call_args[0][0])

        # повторный запуск в тот же день — без дублей
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 1)

        self.set_expiry(self.dealer_a, timedelta(hours=10))
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("через 1 дн.", mail.outbox[1].subject)

        self.set_expiry(self.dealer_a, -timedelta(hours=2))
        result = send_subscription_reminders()
        self.assertEqual(result["expired"], 1)
        self.assertIn("закончился", mail.outbox[2].subject)
        send_subscription_reminders()
        self.assertEqual(len(mail.outbox), 3)

    def test_no_reminder_when_already_renewed(self):
        self.set_expiry(self.dealer_a, timedelta(days=2))
        activate_subscription(self.dealer_a, self.business, 1)  # продление того же тарифа
        send_subscription_reminders()
        self.assertEqual([m for m in mail.outbox if "a@test.kg" in m.to], [])

    def test_new_request_notifies_admin(self):
        client = APIClient()
        client.force_authenticate(self.manager_a)
        with self.captureOnCommitCallbacks(execute=True):
            resp = client.post("/api/dashboard/subscription/requests/", {"plan": self.business.pk, "months": 3, "comment": "звоните после 14"}, format="json")
        self.assertEqual(resp.status_code, 201)
        text = self.telegram.call_args[0][0]
        self.assertIn("Салон А", text)
        self.assertIn("8 070 сом", text)
        self.assertIn("звоните после 14", text)

    def test_cron_endpoint_requires_secret(self):
        anon = APIClient()
        url = "/api/internal/subscription-reminders/"
        self.assertEqual(anon.post(url).status_code, 403)
        self.assertEqual(anon.post(url, HTTP_X_CRON_SECRET="wrong").status_code, 403)
        resp = anon.post(url, HTTP_X_CRON_SECRET="s3cret")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("expiring", resp.data)
        with self.settings(CRON_SECRET=""):
            self.assertEqual(anon.post(url, HTTP_X_CRON_SECRET="").status_code, 404)

    def test_management_command_runs(self):
        from django.core.management import call_command
        PlanRequest.objects.create(dealer=self.dealer_a, plan=self.business)
        out = StringIO()
        call_command("send_subscription_reminders", stdout=out)
        self.assertIn("новых заявок: 1", out.getvalue())
