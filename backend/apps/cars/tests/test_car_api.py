from decimal import Decimal
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.moderation.models import ModerationEvent

from ..models import Brand, Car, CarImage, City, Model


class CarApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="Secure-owner-password-84!",
            phone="+996700123456",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="Secure-other-password-84!",
            phone="+996700123457",
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com",
            password="Secure-admin-password-84!",
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

    def car_payload(self, **overrides):
        payload = {
            "model": self.model.pk,
            "city": self.city.pk,
            "year": 2020,
            "price": "15000.00",
            "mileage": 50000,
            "engine_volume": "2.5",
            "engine_type": Car.EngineType.PETROL,
            "transmission": Car.Transmission.AUTOMATIC,
            "drive_type": Car.DriveType.FWD,
            "body_type": Car.BodyType.SEDAN,
            "condition": Car.Condition.USED,
            "description": "Автомобиль в хорошем состоянии.",
            "contact_phone": "+996700123456",
        }
        payload.update(overrides)
        return payload

    def create_car(self, owner=None, status=Car.Status.DRAFT, **overrides):
        payload = self.car_payload(**overrides)
        model_id = payload.pop("model")
        city_id = payload.pop("city")
        return Car.objects.create(
            owner=owner or self.owner,
            status=status,
            model_id=model_id,
            city_id=city_id,
            **payload,
        )

    def make_image(self, name="car.jpg", image_format="JPEG"):
        buffer = BytesIO()
        Image.new("RGB", (8, 8), color=(25, 80, 140)).save(
            buffer,
            format=image_format,
        )
        return SimpleUploadedFile(
            name,
            buffer.getvalue(),
            content_type=f"image/{image_format.lower()}",
        )

    def test_create_requires_auth_and_ignores_owner_and_status_input(self):
        payload = self.car_payload(
            owner=self.other_user.pk,
            status=Car.Status.PUBLISHED,
        )
        anonymous_response = self.client.post(
            "/api/cars/",
            payload,
            format="json",
        )
        self.assertEqual(anonymous_response.status_code, 401)

        self.client.force_authenticate(user=self.owner)
        response = self.client.post("/api/cars/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        car = Car.objects.get(pk=response.data["id"])
        self.assertEqual(car.owner, self.owner)
        self.assertEqual(car.status, Car.Status.DRAFT)
        self.assertEqual(response.data["brand"], "Toyota")

    def test_public_lookup_endpoints_return_active_catalog_data(self):
        response_brands = self.client.get("/api/brands/")
        response_models = self.client.get(
            "/api/models/",
            {"brand": self.brand.pk},
        )
        response_cities = self.client.get("/api/cities/")

        self.assertEqual(response_brands.status_code, 200)
        self.assertTrue(any(brand["id"] == self.brand.pk for brand in response_brands.data))
        self.assertEqual(response_models.status_code, 200)
        self.assertTrue(any(model["id"] == self.model.pk for model in response_models.data))
        self.assertTrue(any(brand["name"] == "Toyota" for brand in response_brands.data))
        self.assertTrue(any(model["name"] == "Camry" for model in response_models.data))
        self.assertEqual(response_cities.status_code, 200)
        self.assertTrue(any(city["id"] == self.city.pk for city in response_cities.data))

    def test_owner_can_edit_and_only_owner_can_edit_or_delete(self):
        car = self.create_car()

        self.client.force_authenticate(user=self.owner)
        own_update = self.client.patch(
            f"/api/cars/{car.pk}/",
            {"price": "12500.00"},
            format="json",
        )
        self.assertEqual(own_update.status_code, 200)
        car.refresh_from_db()
        self.assertEqual(car.price, Decimal("12500.00"))

        self.client.force_authenticate(user=self.other_user)
        other_update = self.client.patch(
            f"/api/cars/{car.pk}/",
            {"price": "1.00"},
            format="json",
        )
        self.assertEqual(other_update.status_code, 404)
        other_delete = self.client.delete(f"/api/cars/{car.pk}/")
        self.assertEqual(other_delete.status_code, 404)
        self.assertEqual(Car.objects.get(pk=car.pk).status, Car.Status.DRAFT)

    def test_published_detail_is_public_and_draft_detail_is_owner_only(self):
        published = self.create_car(status=Car.Status.PUBLISHED)
        draft = self.create_car()

        public_detail = self.client.get(f"/api/cars/{published.pk}/")
        hidden_draft = self.client.get(f"/api/cars/{draft.pk}/")

        self.assertEqual(public_detail.status_code, 200)
        self.assertEqual(hidden_draft.status_code, 404)

        self.client.force_authenticate(user=self.owner)
        owner_detail = self.client.get(f"/api/cars/{draft.pk}/")
        full_update = self.client.put(
            f"/api/cars/{draft.pk}/",
            self.car_payload(price="17500.00"),
            format="json",
        )
        self.assertEqual(owner_detail.status_code, 200)
        self.assertEqual(full_update.status_code, 200)

    def test_editing_published_listing_sends_it_back_to_moderation(self):
        car = self.create_car(status=Car.Status.PUBLISHED)
        self.client.force_authenticate(user=self.owner)

        response = self.client.patch(
            f"/api/cars/{car.pk}/",
            {"price": "13000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Car.Status.PENDING)
        self.assertEqual(
            ModerationEvent.objects.filter(
                car=car,
                action=ModerationEvent.Action.SUBMITTED,
            ).count(),
            1,
        )

    def test_my_cars_only_returns_current_users_listings(self):
        own_car = self.create_car()
        self.create_car(owner=self.other_user)
        self.client.force_authenticate(user=self.owner)

        response = self.client.get("/api/my-cars/")
        router_response = self.client.get("/api/cars/my-cars/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(own_car.pk))
        self.assertEqual(router_response.status_code, 200)
        self.assertEqual(router_response.data["count"], 1)

    def test_public_catalog_filters_sorts_and_paginates(self):
        cheaper = self.create_car(
            status=Car.Status.PUBLISHED,
            price=Decimal("10000.00"),
            year=2018,
            mileage=80000,
        )
        self.create_car(
            status=Car.Status.PUBLISHED,
            price=Decimal("20000.00"),
            year=2022,
            mileage=20000,
        )
        self.create_car(status=Car.Status.DRAFT, price=Decimal("5000.00"))

        response = self.client.get(
            "/api/cars/",
            {
                "min_price": "9000",
                "max_year": "2025",
                "engine_type": Car.EngineType.PETROL,
                "ordering": "price",
                "page_size": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], str(cheaper.pk))
        second_page = self.client.get(
            "/api/cars/",
            {
                "min_price": "9000",
                "max_year": "2025",
                "engine_type": Car.EngineType.PETROL,
                "ordering": "price",
                "page_size": "1",
                "page": "2",
            },
        )
        self.assertEqual(
            second_page.data["results"][0]["price"],
            "20000.00",
        )

    def test_public_catalog_combines_all_filters_before_pagination(self):
        matching = self.create_car(
            status=Car.Status.PUBLISHED,
            price="15000.00",
            year=2020,
            mileage=50000,
        )
        second_matching = self.create_car(
            status=Car.Status.PUBLISHED,
            price="18000.00",
            year=2022,
            mileage=60000,
        )
        other_model, _ = Model.objects.get_or_create(
            brand=self.brand,
            slug="corolla",
            defaults={"name": "Corolla"},
        )
        other_brand, _ = Brand.objects.get_or_create(
            slug="lexus",
            defaults={"name": "Lexus"},
        )
        other_brand_model, _ = Model.objects.get_or_create(
            brand=other_brand,
            slug="camry",
            defaults={"name": "Camry"},
        )
        other_city = City.objects.get(slug="osh")

        rejected_cars = [
            {"price": "9000.00"},
            {"price": "21000.00"},
            {"year": 2017},
            {"year": 2025},
            {"mileage": 30000},
            {"mileage": 90000},
            {"engine_type": Car.EngineType.DIESEL},
            {"transmission": Car.Transmission.MANUAL},
            {"drive_type": Car.DriveType.AWD},
            {"body_type": Car.BodyType.SUV},
            {"condition": Car.Condition.NEW},
            {
                "model": other_model.pk,
                "description": "Toyota Camry test record.",
            },
            {
                "model": other_brand_model.pk,
                "description": "Toyota Camry test record.",
            },
            {"city": other_city.pk},
        ]
        for overrides in rejected_cars:
            self.create_car(status=Car.Status.PUBLISHED, **overrides)

        params = {
            "search": "Toyota Camry",
            "brand": self.brand.pk,
            "model": self.model.pk,
            "city": self.city.pk,
            "min_price": "10000",
            "max_price": "20000",
            "min_year": "2018",
            "max_year": "2024",
            "min_mileage": "40000",
            "max_mileage": "80000",
            "engine_type": Car.EngineType.PETROL,
            "transmission": Car.Transmission.AUTOMATIC,
            "drive_type": Car.DriveType.FWD,
            "body_type": Car.BodyType.SEDAN,
            "condition": Car.Condition.USED,
            "ordering": "price",
            "page_size": "1",
        }

        first_page = self.client.get("/api/cars/", params)
        params["page"] = "2"
        second_page = self.client.get("/api/cars/", params)

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["count"], 2)
        self.assertEqual(first_page.data["results"][0]["id"], str(matching.pk))
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.data["results"][0]["id"], str(second_matching.pk))

        no_matches = self.client.get("/api/cars/", {"search": "No such vehicle"})
        self.assertEqual(no_matches.data["count"], 0)

    def test_public_catalog_supports_price_year_and_publication_date_ordering(self):
        older = self.create_car(
            status=Car.Status.PUBLISHED,
            price="10000.00",
            year=2018,
        )
        newer = self.create_car(
            status=Car.Status.PUBLISHED,
            price="20000.00",
            year=2022,
        )
        now = timezone.now()
        Car.objects.filter(pk=older.pk).update(
            published_at=now - timedelta(days=2),
        )
        Car.objects.filter(pk=newer.pk).update(
            published_at=now - timedelta(days=1),
        )

        cheaper_first = self.client.get("/api/cars/", {"ordering": "price"})
        expensive_first = self.client.get("/api/cars/", {"ordering": "-price"})
        newest_year_first = self.client.get("/api/cars/", {"ordering": "-year"})
        recently_published_first = self.client.get(
            "/api/cars/",
            {"ordering": "-published_at"},
        )

        self.assertEqual(cheaper_first.data["results"][0]["id"], str(older.pk))
        self.assertEqual(expensive_first.data["results"][0]["id"], str(newer.pk))
        self.assertEqual(newest_year_first.data["results"][0]["id"], str(newer.pk))
        self.assertEqual(
            recently_published_first.data["results"][0]["id"],
            str(newer.pk),
        )

    def test_image_upload_delete_and_publication_moderation_lifecycle(self):
        car = self.create_car()
        self.client.force_authenticate(user=self.owner)

        no_images = self.client.post(f"/api/cars/{car.pk}/submit/")
        self.assertEqual(no_images.status_code, 400)

        upload = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": [self.make_image("front.jpg"), self.make_image("side.png", "PNG")]},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        self.assertEqual(CarImage.objects.filter(car=car).count(), 2)
        self.assertEqual(
            CarImage.objects.filter(car=car, is_cover=True).count(),
            1,
        )
        stored_image = CarImage.objects.filter(car=car).first()
        self.assertIn(f"cars/{car.pk}/", stored_image.image.name)
        self.assertNotIn("front.jpg", stored_image.image.name)
        self.assertTrue(stored_image.image.storage.exists(stored_image.image.name))

        self.client.force_authenticate(user=self.other_user)
        unauthorized_upload = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": [self.make_image("unauthorized.jpg")]},
            format="multipart",
        )
        self.assertEqual(unauthorized_upload.status_code, 404)

        self.client.force_authenticate(user=self.owner)
        cover_id = next(item["id"] for item in upload.data if item["is_cover"])
        side_id = next(item["id"] for item in upload.data if not item["is_cover"])
        image_list = self.client.get(f"/api/cars/{car.pk}/images/")
        self.assertEqual(image_list.status_code, 200)
        self.assertEqual(
            [item["id"] for item in image_list.data],
            [cover_id, side_id],
        )

        reordered = self.client.post(
            f"/api/cars/{car.pk}/images/reorder/",
            {"image_ids": [side_id, cover_id]},
            format="json",
        )
        self.assertEqual(reordered.status_code, 200)
        self.assertEqual(
            [item["id"] for item in reordered.data],
            [side_id, cover_id],
        )
        self.assertEqual(reordered.data[0]["position"], 0)
        self.assertEqual(reordered.data[1]["position"], 1)

        changed_cover = self.client.patch(
            f"/api/cars/{car.pk}/images/{side_id}/",
            {"is_cover": True},
            format="json",
        )
        self.assertEqual(changed_cover.status_code, 200)
        self.assertTrue(changed_cover.data["is_cover"])
        side_image = CarImage.objects.get(pk=side_id)
        side_image_path = side_image.image.name

        with self.captureOnCommitCallbacks(execute=True):
            delete_image = self.client.delete(
                f"/api/cars/{car.pk}/images/{side_id}/"
            )
        self.assertEqual(delete_image.status_code, 204)
        self.assertTrue(CarImage.objects.get(pk=cover_id).is_cover)
        self.assertFalse(side_image.image.storage.exists(side_image_path))

        submitted = self.client.post(f"/api/cars/{car.pk}/submit/")
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.data["status"], Car.Status.PENDING)

        self.client.force_authenticate(user=self.other_user)
        forbidden_approval = self.client.post(f"/api/cars/{car.pk}/approve/")
        self.assertEqual(forbidden_approval.status_code, 403)

        self.client.force_authenticate(user=self.admin)
        queue = self.client.get("/api/cars/moderation-queue/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(queue.data["count"], 1)
        approved = self.client.post(f"/api/cars/{car.pk}/approve/")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], Car.Status.PUBLISHED)

        self.client.force_authenticate(user=self.owner)
        deactivated = self.client.post(f"/api/cars/{car.pk}/deactivate/")
        self.assertEqual(deactivated.data["status"], Car.Status.INACTIVE)
        reactivated = self.client.post(f"/api/cars/{car.pk}/reactivate/")
        self.assertEqual(reactivated.data["status"], Car.Status.PENDING)

        self.client.force_authenticate(user=self.admin)
        rejected = self.client.post(
            f"/api/cars/{car.pk}/reject/",
            {"reason": "Недостаточно информации."},
            format="json",
        )
        self.assertEqual(rejected.data["status"], Car.Status.REJECTED)
        self.assertEqual(
            ModerationEvent.objects.filter(car=car).count(),
            5,
        )

        self.client.force_authenticate(user=self.owner)
        deleted = self.client.delete(f"/api/cars/{car.pk}/")
        self.assertEqual(deleted.status_code, 204)
        car.refresh_from_db()
        self.assertEqual(car.status, Car.Status.REMOVED)
        my_cars = self.client.get("/api/my-cars/")
        self.assertEqual(my_cars.data["count"], 0)
        self.assertEqual(
            self.client.get(f"/api/cars/{car.pk}/").status_code,
            404,
        )

    def test_image_upload_rejects_non_image_files(self):
        car = self.create_car()
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {
                "images": [
                    SimpleUploadedFile(
                        "not-an-image.jpg",
                        b"not an image",
                        content_type="image/jpeg",
                    )
                ]
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(CarImage.objects.filter(car=car).exists())

        mismatched_extension = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": [self.make_image("misleading.png", "JPEG")]},
            format="multipart",
        )
        self.assertEqual(mismatched_extension.status_code, 400)
        self.assertFalse(CarImage.objects.filter(car=car).exists())

    def test_image_list_is_public_only_for_published_cars(self):
        car = self.create_car()
        self.client.force_authenticate(user=self.owner)
        upload = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": [self.make_image()]},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)

        self.client.force_authenticate(user=None)
        hidden_images = self.client.get(f"/api/cars/{car.pk}/images/")
        self.assertEqual(hidden_images.status_code, 404)

        car.status = Car.Status.PUBLISHED
        car.save(update_fields=("status",))
        public_images = self.client.get(f"/api/cars/{car.pk}/images/")
        self.assertEqual(public_images.status_code, 200)
        self.assertEqual(len(public_images.data), 1)

    def test_image_upload_accepts_supported_formats_and_enforces_limits(self):
        car = self.create_car()
        self.client.force_authenticate(user=self.owner)

        supported_formats = [
            self.make_image("one.jpg", "JPEG"),
            self.make_image("two.jpeg", "JPEG"),
            self.make_image("three.png", "PNG"),
            self.make_image("four.webp", "WEBP"),
        ]
        response = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": supported_formats},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 4)

        oversized = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {
                "images": [
                    SimpleUploadedFile(
                        "large.jpg",
                        b"x" * (10 * 1024 * 1024 + 1),
                        content_type="image/jpeg",
                    )
                ]
            },
            format="multipart",
        )
        self.assertEqual(oversized.status_code, 400)

        remaining_count = 20 - CarImage.objects.filter(car=car).count()
        while remaining_count > 0:
            batch_count = min(remaining_count, 10)
            batch = [
                self.make_image(f"extra-{index}.jpg")
                for index in range(batch_count)
            ]
            upload_batch = self.client.post(
                f"/api/cars/{car.pk}/images/",
                {"images": batch},
                format="multipart",
            )
            self.assertEqual(upload_batch.status_code, 201)
            remaining_count -= batch_count

        over_limit = self.client.post(
            f"/api/cars/{car.pk}/images/",
            {"images": [self.make_image("extra.jpg")]},
            format="multipart",
        )
        self.assertEqual(over_limit.status_code, 400)
        self.assertEqual(CarImage.objects.filter(car=car).count(), 20)
