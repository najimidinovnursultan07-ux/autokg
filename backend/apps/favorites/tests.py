from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cars.models import Brand, Car, City, Model
from apps.favorites.models import Favorite


class FavoriteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="favorites@example.com",
            password="Secure-favorites-password-84!",
            phone="+996700123456",
        )
        self.other_user = User.objects.create_user(
            email="other-favorites@example.com",
            password="Secure-other-favorites-password-84!",
            phone="+996700123457",
        )
        brand, _ = Brand.objects.get_or_create(
            slug="toyota",
            defaults={"name": "Toyota"},
        )
        model, _ = Model.objects.get_or_create(
            brand=brand,
            slug="camry",
            defaults={"name": "Camry"},
        )
        city = City.objects.get(slug="bishkek")
        self.car = Car.objects.create(
            owner=self.user,
            model=model,
            city=city,
            year=2020,
            price="15000.00",
            mileage=50000,
            engine_volume="2.5",
            engine_type=Car.EngineType.PETROL,
            transmission=Car.Transmission.AUTOMATIC,
            drive_type=Car.DriveType.FWD,
            body_type=Car.BodyType.SEDAN,
            condition=Car.Condition.USED,
            description="Автомобиль в хорошем состоянии.",
            contact_phone="+996700123456",
            status=Car.Status.PUBLISHED,
        )

    def test_favorites_require_authentication_and_return_car_data(self):
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)
        unauthorized_create = self.client.post(
            "/api/favorites/",
            {"car": str(self.car.pk)},
            format="json",
        )
        self.assertEqual(unauthorized_create.status_code, 401)
        self.assertEqual(Favorite.objects.count(), 0)

        self.client.force_authenticate(user=self.user)
        created = self.client.post(
            "/api/favorites/",
            {"car": str(self.car.pk)},
            format="json",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["car_details"]["id"], str(self.car.pk))
        self.assertEqual(Favorite.objects.filter(user=self.user).count(), 1)

        listed = self.client.get("/api/favorites/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], created.data["id"])
        self.assertEqual(
            listed.data["results"][0]["car_details"]["id"],
            str(self.car.pk),
        )

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get("/api/favorites/").status_code, 401)
        self.client.force_authenticate(user=self.user)
        restored = self.client.get("/api/favorites/")
        self.assertEqual(restored.data["count"], 1)
        self.assertEqual(restored.data["results"][0]["id"], created.data["id"])

        duplicate = self.client.post(
            "/api/favorites/",
            {"car": str(self.car.pk)},
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)

        favorite_id = created.data["id"]
        self.client.force_authenticate(user=self.other_user)
        forbidden_delete = self.client.delete(f"/api/favorites/{favorite_id}/")
        self.assertEqual(forbidden_delete.status_code, 404)
        self.assertTrue(Favorite.objects.filter(pk=favorite_id).exists())

        self.client.force_authenticate(user=self.user)
        deleted = self.client.delete(f"/api/favorites/{favorite_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Favorite.objects.filter(pk=favorite_id).exists())
