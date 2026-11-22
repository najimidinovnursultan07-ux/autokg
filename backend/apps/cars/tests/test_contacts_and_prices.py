from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cars.models import Car, CarPriceHistory
from apps.common.rates import parse_nbkr_xml
from apps.common.testing import MarketplaceTestCase

NBKR_XML = """<?xml version="1.0" encoding="windows-1251" ?>
<CurrencyRates Name="Daily Exchange Rates" Date="21.11.2026">
<Currency ISOCode="USD"><Nominal>1</Nominal><Value>87,4500</Value></Currency>
<Currency ISOCode="EUR"><Nominal>1</Nominal><Value>95,8977</Value></Currency>
</CurrencyRates>""".encode("cp1251")


class ContactRevealTests(MarketplaceTestCase):
    client_class = APIClient

    def setUp(self):
        super().setUp()
        self.dealer_a.whatsapp = "+996700111112"
        self.dealer_a.save()
        self.car = self.make_car(self.dealer_a)

    def test_public_api_hides_phones_and_stats(self):
        detail = self.client.get(f"/api/cars/{self.car.pk}/").data
        listing = self.client.get("/api/cars/").data["results"][0]
        for data in (detail, listing):
            self.assertNotIn("contact_phone", data)
            self.assertNotIn("phone", data["dealer_detail"])
            self.assertNotIn("whatsapp", data["dealer_detail"])
            self.assertNotIn("phone_views", data)
            self.assertTrue(data["has_phone"])
            self.assertTrue(data["has_whatsapp"])
        dealer_page = self.client.get(f"/api/dealers/{self.dealer_a.slug}/").data
        self.assertNotIn("contact_phone", dealer_page["cars"][0])

    def test_reveal_returns_contacts_and_counts_clicks(self):
        url = f"/api/cars/{self.car.pk}/contacts/"
        phone = self.client.post(url, {"kind": "phone"}, format="json")
        self.client.post(url, {"kind": "whatsapp"}, format="json")
        self.client.post(url, {"kind": "whatsapp"}, format="json")

        self.assertEqual(phone.status_code, 200)
        # Номер из объявления важнее номеров салона
        self.assertEqual(phone.data, {"phone": "+996700000002", "whatsapp": "+996700000002"})
        self.car.refresh_from_db()
        self.assertEqual((self.car.phone_views, self.car.whatsapp_clicks), (1, 2))

    def test_reveal_falls_back_to_dealer_contacts(self):
        Car.objects.filter(pk=self.car.pk).update(contact_phone="")
        data = self.client.post(f"/api/cars/{self.car.pk}/contacts/", {"kind": "phone"}, format="json").data
        self.assertEqual(data, {"phone": "+996700111111", "whatsapp": "+996700111112"})

    def test_own_dealer_clicks_are_not_counted_and_stats_visible_in_dashboard(self):
        self.client.force_authenticate(self.manager_a)
        self.client.post(f"/api/cars/{self.car.pk}/contacts/", {"kind": "phone"}, format="json")
        self.car.refresh_from_db()
        self.assertEqual(self.car.phone_views, 0)
        dashboard = self.client.get(f"/api/dashboard/cars/{self.car.pk}/").data
        self.assertIn("phone_views", dashboard)
        self.assertIn("whatsapp_clicks", dashboard)

    def test_invalid_kind_and_hidden_car(self):
        url = f"/api/cars/{self.car.pk}/contacts/"
        self.assertEqual(self.client.post(url, {"kind": "email"}, format="json").status_code, 400)
        self.car.status = Car.Status.HIDDEN
        self.car.save()
        self.assertEqual(self.client.post(url, {"kind": "phone"}, format="json").status_code, 404)

    def test_other_writes_to_public_catalog_still_forbidden(self):
        self.assertEqual(self.client.delete(f"/api/cars/{self.car.pk}/").status_code, 401)


class PriceHistoryTests(MarketplaceTestCase):
    client_class = APIClient

    def test_history_recorded_on_create_and_price_change_only(self):
        car = self.make_car(self.dealer_a, price="1000000.00")
        car.mileage = 20000
        car.save()
        car.price = Decimal("900000.00")
        car.save()
        prices = list(CarPriceHistory.objects.filter(car=car).values_list("price", flat=True))
        self.assertEqual(prices, [Decimal("900000.00"), Decimal("1000000.00")])

    def test_price_drop_shown_after_reduction(self):
        car = self.make_car(self.dealer_a, price="1000000.00")
        car.price = Decimal("900000.00")
        car.save()

        listing = self.client.get("/api/cars/").data["results"][0]
        self.assertEqual(listing["price_drop"]["old_price"], "1000000.00")
        self.assertIsNone(listing["price_history"])  # история — только в карточке объявления
        detail = self.client.get(f"/api/cars/{car.pk}/").data
        self.assertEqual([p["price"] for p in detail["price_history"]], ["900000.00", "1000000.00"])

    def test_no_drop_for_increase_old_change_or_currency_switch(self):
        up = self.make_car(self.dealer_a, price="1000000.00")
        up.price = Decimal("1100000.00")
        up.save()

        old = self.make_car(self.dealer_a, price="1000000.00")
        old.price = Decimal("800000.00")
        old.save()
        CarPriceHistory.objects.filter(car=old, price=Decimal("800000.00")).update(
            created_at=timezone.now() - timedelta(days=45)
        )

        switched = self.make_car(self.dealer_a, price="1000000.00")
        switched.price, switched.currency = Decimal("12000.00"), "USD"
        switched.save()

        for car in (up, old, switched):
            self.assertIsNone(self.client.get(f"/api/cars/{car.pk}/").data["price_drop"], car.price)


class ExchangeRatesTests(MarketplaceTestCase):
    client_class = APIClient

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_parse_nbkr_xml(self):
        data = parse_nbkr_xml(NBKR_XML)
        self.assertEqual(data["date"], "21.11.2026")
        self.assertEqual(data["rates"]["USD"], "87.4500")

    def test_rates_endpoint_caches_and_survives_nbkr_outage(self):
        with mock.patch("apps.common.rates.fetch_nbkr_rates", return_value=parse_nbkr_xml(NBKR_XML)) as fetch:
            self.assertEqual(self.client.get("/api/rates/").data["rates"]["USD"], "87.4500")
            self.client.get("/api/rates/")
        self.assertEqual(fetch.call_count, 1)

        cache.delete("nbkr_rates")
        with mock.patch("apps.common.rates.fetch_nbkr_rates", side_effect=OSError("down")):
            self.assertEqual(self.client.get("/api/rates/").data["rates"]["USD"], "87.4500")
        cache.clear()
        with mock.patch("apps.common.rates.fetch_nbkr_rates", side_effect=OSError("down")):
            self.assertEqual(self.client.get("/api/rates/").status_code, 503)
