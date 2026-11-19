from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.dealers.models import Dealer
from apps.favorites.models import Favorite
from apps.favorites.serializers import FavoriteSerializer

from ..models import Brand, Car, CarImage, City, Model
from ..serializers import CarSerializer


class CarModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="seller@example.com",
            password="Secure-test-password-74!",
            phone="+996700123456",
        )
        self.brand, _ = Brand.objects.get_or_create(
            slug="toyota",
            defaults={"name": "Toyota"},
        )
        self.model, _ = Model.objects.get_or_create(
            brand=self.brand,
            slug="camry",
            defaults={"name": "Camry"},
        )
        self.city, _ = City.objects.get_or_create(
            slug="bishkek",
            defaults={"name": "Бишкек"},
        )

    def create_car(self, **overrides):
        fields = {
            "owner": self.user,
            "dealer": Dealer.objects.get_or_create(slug="salon", defaults={"name": "Салон"})[0],
            "model": self.model,
            "city": self.city,
            "year": 2020,
            "price": Decimal("15000.00"),
            "mileage": 50000,
            "engine_volume": Decimal("2.5"),
            "engine_type": Car.EngineType.PETROL,
            "transmission": Car.Transmission.AUTOMATIC,
            "drive_type": Car.DriveType.FWD,
            "body_type": Car.BodyType.SEDAN,
            "condition": Car.Condition.USED,
            "description": "Автомобиль в хорошем состоянии.",
            "contact_phone": "+996700123456",
        }
        fields.update(overrides)
        return Car.objects.create(**fields)

    def test_brand_is_resolved_through_model_and_serialized(self):
        car = self.create_car()

        self.assertEqual(car.brand, self.brand)
        self.assertEqual(CarSerializer(car).data["brand"], "Toyota")
        self.assertEqual(CarSerializer(car).data["model"], self.model.pk)

    def test_kyrgyzstan_city_seed_migration_includes_major_cities(self):
        self.assertTrue(City.objects.filter(slug="bishkek").exists())
        self.assertTrue(City.objects.filter(slug="osh").exists())

    def test_price_database_constraint_rejects_negative_value(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_car(price=Decimal("-1.00"))

    def test_required_car_fields_are_validated_by_serializer(self):
        serializer = CarSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertIn("model", serializer.errors)
        self.assertIn("city", serializer.errors)
        self.assertIn("year", serializer.errors)
        self.assertIn("price", serializer.errors)

    def test_favorite_many_to_many_uses_unique_through_record(self):
        car = self.create_car(status=Car.Status.ACTIVE)
        Favorite.objects.create(user=self.user, car=car)

        self.assertEqual(list(self.user.favorite_cars.all()), [car])
        serializer = FavoriteSerializer(
            data={"car": str(car.pk)},
            context={"request": type("Request", (), {"user": self.user})()},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("car", serializer.errors)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Favorite.objects.create(user=self.user, car=car)

    def test_only_one_cover_image_is_allowed_per_car(self):
        car = self.create_car()
        CarImage.objects.create(
            car=car,
            image="cars/first.jpg",
            position=0,
            is_cover=True,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CarImage.objects.create(
                car=car,
                image="cars/second.jpg",
                position=1,
                is_cover=True,
            )
