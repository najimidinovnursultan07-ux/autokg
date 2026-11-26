from rest_framework.test import APIClient

from apps.common.testing import MarketplaceTestCase


class MurabahaTests(MarketplaceTestCase):
    client_class = APIClient

    URL = "/api/dashboard/dealer/"

    def test_disabled_by_default_and_hidden_in_car(self):
        car = self.make_car(self.dealer_a)
        data = self.client.get(f"/api/cars/{car.pk}/").data
        self.assertIsNone(data["dealer_detail"]["murabaha"])

    def test_manager_sets_terms_and_they_appear_in_car(self):
        self.client.force_authenticate(self.manager_a)
        response = self.client.patch(self.URL, {
            "murabaha_enabled": "true",
            "murabaha_markup_percent": "12.5",
            "murabaha_min_down_percent": "20",
            "murabaha_max_term_months": "36",
            "murabaha_note": "Без скрытых комиссий",
        }, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["murabaha_enabled"])

        car = self.make_car(self.dealer_a)
        self.client.force_authenticate(None)
        murabaha = self.client.get(f"/api/cars/{car.pk}/").data["dealer_detail"]["murabaha"]
        self.assertEqual(murabaha, {
            "markup_percent": 12.5, "min_down_percent": 20,
            "max_term_months": 36, "note": "Без скрытых комиссий",
        })

    def test_validation(self):
        self.client.force_authenticate(self.manager_a)
        for bad in (
            {"murabaha_markup_percent": "-1"},
            {"murabaha_markup_percent": "101"},
            {"murabaha_min_down_percent": "95"},
            {"murabaha_max_term_months": "2"},
            {"murabaha_max_term_months": "121"},
        ):
            response = self.client.patch(self.URL, bad, format="json")
            self.assertEqual(response.status_code, 400, bad)
