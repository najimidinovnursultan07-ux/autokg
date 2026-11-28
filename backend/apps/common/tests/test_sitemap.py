from django.test import override_settings
from rest_framework.test import APIClient

from apps.cars.models import Car
from apps.common.testing import MarketplaceTestCase
from apps.subscriptions.models import Plan
from apps.subscriptions.services import activate_subscription


@override_settings(FRONTEND_URL="https://autobuy.test")
class SitemapTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        activate_subscription(self.dealer_a, Plan.objects.get(code="business"), 1, amount="2100", payment_method="cash")

    def get_xml(self):
        resp = APIClient().get("/api/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/xml", resp["Content-Type"])
        return resp.content.decode()

    def test_lists_public_pages_dealers_and_active_cars(self):
        active = self.make_car(self.dealer_a)
        sold = self.make_car(self.dealer_a, status=Car.Status.SOLD)
        xml = self.get_xml()
        self.assertIn("<loc>https://autobuy.test/</loc>", xml)
        self.assertIn("<loc>https://autobuy.test/catalog</loc>", xml)
        self.assertIn("<loc>https://autobuy.test/dealers/salon-a</loc>", xml)
        self.assertIn(f"<loc>https://autobuy.test/cars/{active.id}</loc>", xml)
        self.assertNotIn(str(sold.id), xml)
        self.assertNotIn("/dashboard", xml)

    def test_hides_inactive_dealer_and_its_cars(self):
        self.dealer_b.is_active = False
        self.dealer_b.save()
        hidden = self.make_car(self.dealer_b)
        xml = self.get_xml()
        self.assertNotIn("salon-b", xml)
        self.assertNotIn(str(hidden.id), xml)
