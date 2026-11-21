from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase, car_payload
from apps.subscriptions.models import Plan
from apps.subscriptions.services import activate_subscription


class ListingExpiryTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        self.anon = APIClient()

    def create(self, **extra):
        resp = self.client_a.post("/api/dashboard/cars/", car_payload(self.model, self.city, **extra), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        return Car.objects.get(pk=resp.data["id"])

    def expire(self, car):
        Car.objects.filter(pk=car.pk).update(expires_at=timezone.now() - timedelta(minutes=1))

    def test_default_30_days_and_choice(self):
        car = self.create()
        self.assertAlmostEqual((car.expires_at - timezone.now()).days, 29, delta=1)
        car = self.create(duration_days=7)
        self.assertAlmostEqual((car.expires_at - timezone.now()).days, 6, delta=1)
        car = self.create(duration_days=0)
        self.assertIsNone(car.expires_at)
        resp = self.client_a.post("/api/dashboard/cars/", car_payload(self.model, self.city, duration_days=5), format="json")
        self.assertEqual(resp.status_code, 400)

    def test_expired_hidden_from_site_and_renewable(self):
        car = self.create()
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 200)
        self.expire(car)
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 404)
        own = self.client_a.get(f"/api/dashboard/cars/{car.pk}/").data
        self.assertTrue(own["is_expired"])
        ids = [c["id"] for c in self.client_a.get("/api/dashboard/cars/?expired=1").data["results"]]
        self.assertEqual(ids, [str(car.pk)])
        # обычная правка не продлевает
        self.client_a.patch(f"/api/dashboard/cars/{car.pk}/", {"price": "700000.00"}, format="json")
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 404)
        # продление
        resp = self.client_a.patch(f"/api/dashboard/cars/{car.pk}/", {"duration_days": 14, "status": "active"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertFalse(resp.data["is_expired"])
        self.assertEqual(self.anon.get(f"/api/cars/{car.pk}/").status_code, 200)

    def test_expired_do_not_count_toward_limit_and_renewal_checks_it(self):
        activate_subscription(self.dealer_a, Plan.objects.get(code="start"), 1)  # лимит 10
        cars = [self.make_car(self.dealer_a) for _ in range(10)]
        self.expire(cars[0])
        self.create()  # место освободилось
        resp = self.client_a.patch(f"/api/dashboard/cars/{cars[0].pk}/", {"duration_days": 30}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("лимит", str(resp.data).lower())

    def test_cannot_promote_expired(self):
        car = self.create()
        self.expire(car)
        resp = self.client_a.post("/api/dashboard/promote/", {"car_id": car.pk, "promotion_type": "top"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Срок размещения истёк", str(resp.data))
