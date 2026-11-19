"""Общие фабрики для тестов."""
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.accounts.models import User
from apps.cars.models import Brand, Car, City, Model
from apps.dealers.models import Dealer

PASSWORD = "Secure-test-password-84!"
LOCAL_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


def make_image(name="car.jpg", fmt="JPEG", size=(8, 8)):
    buffer = BytesIO()
    Image.new("RGB", size, color=(25, 80, 140)).save(buffer, format=fmt)
    content_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[fmt]
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def car_payload(model, city, **overrides):
    data = {
        "model": model.pk,
        "city": city.pk,
        "year": 2020,
        "price": "500000.00",
        "currency": "KGS",
        "mileage": 50000,
        "engine_type": "petrol",
        "transmission": "automatic",
        "drive_type": "fwd",
        "body_type": "sedan",
        "condition": "used",
        "color": "белый",
        "description": "Тестовое объявление",
        "contact_phone": "+996700000001",
    }
    data.update(overrides)
    return data


@override_settings(STORAGES=LOCAL_STORAGES)
class MarketplaceTestCase(TestCase):
    """Справочники, два салона, менеджеры, админ, временная папка media."""

    def setUp(self):
        cache.clear()
        self.media_dir = TemporaryDirectory()
        media = override_settings(MEDIA_ROOT=self.media_dir.name)
        media.enable()
        self.addCleanup(media.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.brand, _ = Brand.objects.get_or_create(slug="toyota", defaults={"name": "Toyota"})
        self.model, _ = Model.objects.get_or_create(
            brand=self.brand, slug="camry", defaults={"name": "Camry"}
        )
        self.city, _ = City.objects.get_or_create(slug="bishkek", defaults={"name": "Бишкек"})

        self.dealer_a = Dealer.objects.create(name="Салон А", slug="salon-a", phone="+996700111111")
        self.dealer_b = Dealer.objects.create(name="Салон Б", slug="salon-b", phone="+996700222222")
        self.manager_a = self.make_manager("a@test.kg", self.dealer_a)
        self.manager_b = self.make_manager("b@test.kg", self.dealer_b)
        self.admin = User.objects.create_superuser(email="admin@test.kg", password=PASSWORD)

    def make_manager(self, email, dealer, **extra):
        return User.objects.create_user(
            email=email, password=PASSWORD, role=User.Role.DEALER, dealer=dealer, **extra
        )

    def make_car(self, dealer, **overrides):
        fields = {
            "owner": dealer.managers.first() or self.admin,
            "dealer": dealer,
            "model": self.model,
            "city": self.city,
            "year": 2020,
            "price": "800000.00",
            "mileage": 10000,
            "engine_type": Car.EngineType.PETROL,
            "transmission": Car.Transmission.AUTOMATIC,
            "drive_type": Car.DriveType.FWD,
            "body_type": Car.BodyType.SEDAN,
            "condition": Car.Condition.USED,
            "description": "Описание",
            "contact_phone": "+996700000002",
            "status": Car.Status.ACTIVE,
        }
        fields.update(overrides)
        return Car.objects.create(**fields)
