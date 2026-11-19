from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import RequestFactory
from django.test.utils import override_settings
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.cars.models import Brand, Car, CarImage, City, Model
from apps.dealers.models import Dealer


class AdminApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Secure-admin-password-84!",
        )
        self.user = User.objects.create_user(
            email="buyer@example.com",
            password="Secure-buyer-password-84!",
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
        self.city = City.objects.get(slug="bishkek")
        self.dealer = Dealer.objects.create(name="Салон", slug="salon")

    def create_car(self, *, status=Car.Status.ACTIVE, owner=None):
        return Car.objects.create(
            owner=owner or self.user,
            dealer=self.dealer,
            model=self.model,
            city=self.city,
            year=2020,
            price="15000.00",
            mileage=50000,
            engine_type=Car.EngineType.PETROL,
            transmission=Car.Transmission.AUTOMATIC,
            drive_type=Car.DriveType.FWD,
            body_type=Car.BodyType.SEDAN,
            condition=Car.Condition.USED,
            description="Автомобиль в хорошем состоянии.",
            contact_phone="+996700123456",
            status=status,
        )

    def make_image(self):
        buffer = BytesIO()
        Image.new("RGB", (8, 8), color=(25, 80, 140)).save(buffer, format="JPEG")
        return SimpleUploadedFile(
            "car.jpg",
            buffer.getvalue(),
            content_type="image/jpeg",
        )

    def login_as_admin(self):
        self.client.force_authenticate(user=self.admin)

    def test_non_admin_cannot_access_admin_api_or_moderation(self):
        car = self.create_car()
        staff_user = User.objects.create_user(
            email="staff@example.com",
            password="Secure-staff-password-84!",
            is_staff=True,
        )
        role_only_admin = User.objects.create_user(
            email="role-admin@example.com",
            password="Secure-role-admin-password-84!",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=self.user)
        admin_paths = (
            "/api/admin/stats/",
            "/api/admin/users/",
            "/api/admin/cars/",
            "/api/admin/brands/",
            "/api/admin/models/",
            "/api/admin/cities/",
        )

        for path in admin_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)

        self.assertEqual(
            self.client.delete(f"/api/admin/cars/{car.pk}/").status_code,
            403,
        )
        self.client.force_authenticate(user=staff_user)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 403)
        request = RequestFactory().get("/django-admin/")
        request.user = staff_user
        self.assertFalse(admin.site.has_permission(request))
        self.client.force_authenticate(user=role_only_admin)
        self.assertEqual(self.client.get("/api/admin/stats/").status_code, 403)

    def test_admin_users_search_pagination_block_and_unblock(self):
        second_user = User.objects.create_user(
            email="seller@example.com",
            password="Secure-seller-password-84!",
            phone="+996700123457",
        )
        third_user = User.objects.create_user(
            email="another@example.com",
            password="Secure-another-password-84!",
            phone="+996700123458",
        )
        self.create_car(owner=second_user)
        self.login_as_admin()

        results = self.client.get(
            "/api/admin/users/",
            {"search": "seller@example.com", "page_size": 1},
        )
        self.assertEqual(results.status_code, 200)
        self.assertEqual(results.data["count"], 1)
        self.assertEqual(results.data["results"][0]["email"], second_user.email)
        self.assertEqual(results.data["results"][0]["listings_count"], 1)

        paginated = self.client.get("/api/admin/users/", {"page_size": 1})
        self.assertEqual(paginated.status_code, 200)
        self.assertEqual(paginated.data["count"], 4)
        self.assertIsNotNone(paginated.data["next"])

        refresh_token = RefreshToken.for_user(second_user)
        blocked = self.client.post(f"/api/admin/users/{second_user.pk}/block/")
        self.assertEqual(blocked.status_code, 200)
        self.assertFalse(blocked.data["is_active"])
        self.assertEqual(
            self.client.post(f"/api/admin/users/{second_user.pk}/unblock/").status_code,
            200,
        )
        self.assertTrue(User.objects.get(pk=second_user.pk).is_active)
        with self.assertRaises(TokenError):
            refresh_token.check_blacklist()

        self.assertEqual(self.client.post(f"/api/admin/users/{third_user.pk}/block/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/admin/users/{third_user.pk}/block/").status_code, 200)
        self.assertEqual(
            self.client.post(f"/api/admin/users/{self.admin.pk}/block/").status_code,
            400,
        )

    def test_admin_car_list_filtering_and_hard_delete(self):
        hidden = self.create_car(status=Car.Status.HIDDEN)
        self.create_car()
        self.login_as_admin()

        filtered = self.client.get(
            "/api/admin/cars/",
            {"status": Car.Status.HIDDEN, "search": "buyer@example.com"},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["id"], str(hidden.pk))

        deleted = self.client.delete(f"/api/admin/cars/{hidden.pk}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Car.objects.filter(pk=hidden.pk).exists())

    def test_admin_can_manage_catalog(self):
        self.create_car()
        self.login_as_admin()

        brand = self.client.post(
            "/api/admin/brands/",
            {"name": "Test Honda", "slug": "test-honda", "is_active": True},
            format="json",
        )
        self.assertEqual(brand.status_code, 201)
        model = self.client.post(
            "/api/admin/models/",
            {
                "brand": brand.data["id"],
                "name": "Test Civic",
                "slug": "test-civic",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(model.status_code, 201)
        deactivated_brand = self.client.patch(
            f"/api/admin/brands/{brand.data['id']}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(deactivated_brand.status_code, 200)
        self.assertFalse(deactivated_brand.data["is_active"])
        city = self.client.post(
            "/api/admin/cities/",
            {"name": "Тестовый город", "slug": "test-city", "is_active": True},
            format="json",
        )
        self.assertEqual(city.status_code, 201)
        self.assertEqual(
            self.client.delete(f"/api/admin/brands/{self.brand.pk}/").status_code,
            409,
        )
