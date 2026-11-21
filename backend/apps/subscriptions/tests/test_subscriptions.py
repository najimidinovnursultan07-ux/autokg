from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase, car_payload
from apps.dealers.models import Dealer
from apps.subscriptions.models import Plan, PlanRequest, Subscription
from apps.subscriptions.services import activate_subscription, add_months, current_subscription


class SubscriptionTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.start = Plan.objects.get(code="start")
        self.business = Plan.objects.get(code="business")
        self.premium = Plan.objects.get(code="premium")
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        self.anon = APIClient()

    def expire(self, dealer):
        past = timezone.now() - timedelta(days=1)
        Subscription.objects.filter(dealer=dealer).update(
            starts_at=past - timedelta(days=14), expires_at=past
        )

    # ── пробный период и видимость ──
    def test_new_dealer_gets_14_day_business_trial(self):
        dealer = Dealer.objects.create(name="Новый салон")
        sub = current_subscription(dealer)
        self.assertEqual(sub.plan, self.business)
        self.assertTrue(sub.is_trial)
        self.assertAlmostEqual((sub.expires_at - sub.starts_at).days, 14)

    def test_cars_hidden_without_subscription_and_return_after_renewal(self):
        car = self.make_car(self.dealer_a)
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 200)
        self.expire(self.dealer_a)
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 404)
        ids = {c["id"] for c in self.anon.get("/api/cars/").data["results"]}
        self.assertNotIn(str(car.pk), ids)
        # страница салона остаётся, но без машин
        resp = self.anon.get(f"/api/dealers/{self.dealer_a.slug}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["cars"], [])
        self.assertEqual(resp.data["dealer"]["car_count"], 0)
        # продлили — объявление вернулось, статус не менялся
        activate_subscription(self.dealer_a, self.start, 1)
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 200)

    # ── лимит объявлений ──
    def test_cannot_publish_over_limit_but_can_save_hidden(self):
        activate_subscription(self.dealer_a, self.start, 1)  # лимит 10
        for _ in range(10):
            self.make_car(self.dealer_a)
        payload = car_payload(self.model, self.city)
        resp = self.client_a.post("/api/dashboard/cars/", payload, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("лимит", str(resp.data).lower())
        resp = self.client_a.post("/api/dashboard/cars/", {**payload, "status": "hidden"}, format="json")
        self.assertEqual(resp.status_code, 201)
        hidden_id = resp.data["id"]
        # публикация скрытого тоже упирается в лимит
        resp = self.client_a.patch(f"/api/dashboard/cars/{hidden_id}/", {"status": "active"}, format="json")
        self.assertEqual(resp.status_code, 400)
        # продали одну — место освободилось
        sold = Car.objects.filter(dealer=self.dealer_a, status="active").first()
        Car.objects.filter(pk=sold.pk).update(status="sold")
        resp = self.client_a.patch(f"/api/dashboard/cars/{hidden_id}/", {"status": "active"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_editing_active_car_at_limit_is_allowed(self):
        activate_subscription(self.dealer_a, self.start, 1)
        cars = [self.make_car(self.dealer_a) for _ in range(10)]
        resp = self.client_a.patch(f"/api/dashboard/cars/{cars[0].pk}/", {"price": "1000.00"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_cannot_publish_without_subscription(self):
        self.expire(self.dealer_a)
        resp = self.client_a.post("/api/dashboard/cars/", car_payload(self.model, self.city), format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Тариф не активен", str(resp.data))

    # ── бонусы продвижения ──
    def test_promotion_uses_monthly_bonus(self):
        activate_subscription(self.dealer_a, self.start, 1)  # 1 ТОП в месяц
        car1, car2 = self.make_car(self.dealer_a), self.make_car(self.dealer_a)
        resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car1.pk, "promotion_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["usage"]["promotions"]["top"]["left"], 0)
        # повторно на ту же машину — уже действует
        resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car1.pk, "promotion_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 400)
        # бонусы закончились
        resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car2.pk, "promotion_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("закончились", str(resp.data))

    def test_premium_urgent_is_unlimited(self):
        activate_subscription(self.dealer_a, self.premium, 1)
        for _ in range(3):
            car = self.make_car(self.dealer_a)
            resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car.pk, "promotion_type": "urgent"}, format="json")
            self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.data["usage"]["promotions"]["urgent"]["left"])

    def test_cannot_promote_other_dealers_car(self):
        car_b = self.make_car(self.dealer_b)
        resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car_b.pk, "promotion_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_online_payment_is_disabled(self):
        car = self.make_car(self.dealer_a)
        resp = self.client_a.post("/api/payments/create/", {"car_id": car.pk, "service_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 410)

    # ── заявки и включение админом ──
    def test_dealer_request_then_admin_activates(self):
        resp = self.client_a.post("/api/dashboard/subscription/requests/", {"plan": self.premium.pk, "months": 3}, format="json")
        self.assertEqual(resp.status_code, 201)
        # повторная заявка заменяет необработанную
        resp = self.client_a.post("/api/dashboard/subscription/requests/", {"plan": self.premium.pk, "months": 12}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(PlanRequest.objects.filter(dealer=self.dealer_a).count(), 1)
        request_id = resp.data["id"]

        self.assertEqual(self.client_a.get("/api/admin/plan-requests/").status_code, 403)
        resp = self.admin_client.post("/api/admin/subscriptions/", {
            "dealer": self.dealer_a.pk, "plan": self.premium.pk, "months": 12,
            "amount": "79900", "payment_method": "transfer", "request_id": request_id,
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(current_subscription(self.dealer_a).plan, self.premium)
        self.assertEqual(PlanRequest.objects.get(pk=request_id).status, "done")

        data = self.client_a.get("/api/dashboard/subscription/").data
        self.assertEqual(data["subscription"]["plan"]["code"], "premium")
        self.assertEqual(data["usage"]["max_active_cars"], 150)

    def test_same_plan_extends_other_plan_replaces(self):
        trial = current_subscription(self.dealer_a)  # пробный «Бизнес»
        first = activate_subscription(self.dealer_a, self.business, 1)
        self.assertEqual(first.starts_at, trial.expires_at)  # пробные дни не сгорают
        second = activate_subscription(self.dealer_a, self.business, 3)
        self.assertEqual(second.starts_at, first.expires_at)
        self.assertEqual(current_subscription(self.dealer_a).pk, trial.pk)
        third = activate_subscription(self.dealer_a, self.start, 1)
        self.assertEqual(current_subscription(self.dealer_a).pk, third.pk)
        self.assertFalse(Subscription.objects.filter(pk=second.pk).exists())

    def test_admin_deactivate_hides_cars(self):
        car = self.make_car(self.dealer_a)
        resp = self.admin_client.post("/api/admin/subscriptions/deactivate/", {"dealer": self.dealer_a.pk}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(current_subscription(self.dealer_a))
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 404)

    def test_admin_overview_lists_all_dealers(self):
        rows = self.admin_client.get("/api/admin/subscriptions/overview/").data
        self.assertEqual({r["dealer"] for r in rows}, {self.dealer_a.pk, self.dealer_b.pk})

    # ── витрина ──
    def test_public_plans_and_dealer_badge_order(self):
        self.assertEqual([p["code"] for p in self.anon.get("/api/plans/").data], ["start", "business", "premium"])
        activate_subscription(self.dealer_a, self.start, 1)
        activate_subscription(self.dealer_b, self.premium, 1)
        self.make_car(self.dealer_b)
        dealers = self.anon.get("/api/dealers/").data
        self.assertEqual(dealers[0]["slug"], "salon-b")
        self.assertTrue(dealers[0]["is_verified"])
        self.assertFalse(dealers[1]["is_verified"])
        featured = self.anon.get("/api/dealers/?featured=1").data
        self.assertEqual([d["slug"] for d in featured], ["salon-b"])

    def test_stats_export_only_on_premium(self):
        self.make_car(self.dealer_a)
        self.assertEqual(self.client_a.get("/api/dashboard/stats-export/").status_code, 403)
        activate_subscription(self.dealer_a, self.premium, 1)
        resp = self.client_a.get("/api/dashboard/stats-export/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Camry", resp.content.decode("utf-8"))

    def test_add_months_clamps_day(self):
        dt = timezone.now().replace(year=2026, month=1, day=31)
        self.assertEqual(add_months(dt, 1).day, 28)
        self.assertEqual(add_months(dt, 12).year, 2027)
