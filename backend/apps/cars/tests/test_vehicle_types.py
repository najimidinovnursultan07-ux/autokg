from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from apps.cars.models import Brand, Car, Model
from apps.common.testing import MarketplaceTestCase, car_payload


class VehicleTypeTests(MarketplaceTestCase):
    URL = "/api/dashboard/cars/"

    def setUp(self):
        super().setUp()
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        brand, _ = Brand.objects.get_or_create(slug="test-bikes", defaults={"name": "Test Bikes"})
        self.bike_model = Model.objects.create(brand=brand, name="Trail", slug="trail", vehicle_type="bicycle")
        self.moto_model = Model.objects.create(brand=brand, name="Moped", slug="moped", vehicle_type="moto")

    def create(self, model, **overrides):
        payload = car_payload(model, self.city, **overrides)
        return self.client_a.post(self.URL, payload, format="json")

    def test_seed_catalog_has_all_vehicle_types(self):
        types = set(Model.objects.values_list("vehicle_type", flat=True))
        self.assertTrue({"car", "moto", "muravey", "bicycle", "scooter"} <= types)

    def test_car_by_default_and_requires_specs(self):
        response = self.create(self.model)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["vehicle_type"], "car")
        response = self.create(self.model, transmission="", body_type="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("transmission", response.data["error"]["details"])
        self.assertIn("body_type", response.data["error"]["details"])

    def test_bicycle_without_engine_and_car_specs(self):
        response = self.create(
            self.bike_model, engine_type="", transmission="", drive_type="", body_type="",
            mileage=0, engine_volume=None,
        )
        self.assertEqual(response.status_code, 201, response.data)
        car = Car.objects.get(pk=response.data["id"])
        self.assertEqual(car.vehicle_type, "bicycle")
        self.assertEqual((car.transmission, car.drive_type, car.body_type), ("", "", ""))

    def test_bicycle_drops_car_only_specs(self):
        # Форма прислала «автомобильные» поля — для велосипеда они очищаются
        response = self.create(self.bike_model)
        self.assertEqual(response.status_code, 201, response.data)
        car = Car.objects.get(pk=response.data["id"])
        self.assertEqual((car.engine_type, car.transmission, car.body_type), ("", "", ""))

    def test_moto_requires_fuel_only(self):
        response = self.create(self.moto_model, engine_type="", drive_type="", body_type="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("engine_type", response.data["error"]["details"])
        response = self.create(self.moto_model, transmission="", drive_type="", body_type="")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["vehicle_type"], "moto")

    def test_vehicle_type_must_match_model(self):
        response = self.create(self.bike_model, vehicle_type="car")
        self.assertEqual(response.status_code, 400)
        self.assertIn("model", response.data["error"]["details"])

    def test_catalog_filter(self):
        car = self.make_car(self.dealer_a)
        bike = self.create(self.bike_model).data["id"]
        anon = APIClient()
        ids = [c["id"] for c in anon.get("/api/cars/", {"vehicle_type": "bicycle"}).data["results"]]
        self.assertEqual(ids, [bike])
        ids = [c["id"] for c in anon.get("/api/cars/", {"vehicle_type": "car"}).data["results"]]
        self.assertEqual(ids, [str(car.pk)])

    def test_db_requires_specs_for_cars(self):
        car = self.make_car(self.dealer_a)
        car.body_type = ""
        with self.assertRaises(IntegrityError), transaction.atomic():
            car.save()

    def test_models_lookup_exposes_vehicle_type(self):
        data = APIClient().get("/api/models/").data
        rows = data["results"] if isinstance(data, dict) else data
        self.assertIn("bicycle", {row["vehicle_type"] for row in rows})

    def test_model_vehicle_type_locked_when_used(self):
        admin = APIClient()
        admin.force_authenticate(self.admin)
        self.create(self.bike_model)
        url = f"/api/admin/models/{self.bike_model.pk}/"
        self.assertEqual(admin.patch(url, {"vehicle_type": "car"}, format="json").status_code, 400)
        self.assertEqual(admin.patch(f"/api/admin/models/{self.moto_model.pk}/", {"vehicle_type": "scooter"}, format="json").status_code, 200)
