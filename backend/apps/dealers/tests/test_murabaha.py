from rest_framework.test import APIClient

from apps.common.testing import MarketplaceTestCase


class MurabahaTests(MarketplaceTestCase):
    client_class = APIClient

    URL = "/api/dashboard/dealer/"
    TERMS = {
        "murabaha_enabled": True,
        "murabaha_markup_percent": "12.5",
        "murabaha_min_down_percent": 20,
        "murabaha_max_term_months": 36,
        "murabaha_note": "Без скрытых комиссий",
    }

    def murabaha_of(self, car):
        self.client.force_authenticate(None)
        return self.client.get(f"/api/cars/{car.pk}/").data["murabaha"]

    def enable_for_dealer(self):
        self.client.force_authenticate(self.manager_a)
        response = self.client.patch(self.URL, self.TERMS, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["murabaha_enabled"])

    def test_disabled_by_default(self):
        car = self.make_car(self.dealer_a)
        self.assertFalse(car.murabaha_available)
        self.assertIsNone(self.murabaha_of(car))

    def test_only_marked_cars_get_calculator(self):
        self.enable_for_dealer()
        marked = self.make_car(self.dealer_a, murabaha_available=True)
        unmarked = self.make_car(self.dealer_a)
        self.assertEqual(self.murabaha_of(marked), {
            "markup_percent": 12.5, "min_down_percent": 20,
            "max_term_months": 36, "note": "Без скрытых комиссий",
        })
        self.assertIsNone(self.murabaha_of(unmarked))

    def test_marked_car_hidden_when_dealer_disables_murabaha(self):
        car = self.make_car(self.dealer_a, murabaha_available=True)
        self.assertIsNone(self.murabaha_of(car))

    def test_manager_marks_car_in_dashboard(self):
        self.enable_for_dealer()
        car = self.make_car(self.dealer_a)
        self.client.force_authenticate(self.manager_a)
        response = self.client.patch(
            f"/api/dashboard/cars/{car.pk}/", {"murabaha_available": True}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(self.murabaha_of(car))

    def test_catalog_filter(self):
        marked = self.make_car(self.dealer_a, murabaha_available=True)
        self.make_car(self.dealer_a)
        self.make_car(self.dealer_b, murabaha_available=True)  # салон Б мурабаху не включал
        self.enable_for_dealer()
        self.client.force_authenticate(None)
        ids = [car["id"] for car in self.client.get("/api/cars/", {"murabaha": "true"}).data["results"]]
        self.assertEqual(ids, [str(marked.pk)])
        self.assertEqual(self.client.get("/api/cars/").data["count"], 3)

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
