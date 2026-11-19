"""
Права доступа закрытой модели (6 обязательных сценариев + рабочие пути).

1) аноним не может создать машину (401);
2) dealer A не может изменить или удалить машину dealer B (404);
3) dealer не может подставить чужой dealer в теле запроса;
4) dealer заблокированного салона не может публиковать;
5) dealer не может зайти в /api/admin/*;
6) dealer не может загрузить фото в папку чужого салона. Загрузка идёт через
   Django (signed upload не используется), поэтому эндпоинта подписи нет вообще,
   а загрузка в чужую машину возвращает 404.
"""
import os

from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cars.models import Car, CarImage
from apps.common.testing import PASSWORD, MarketplaceTestCase, car_payload, make_image
from apps.dealers.models import Dealer


class ClosedMarketplacePermissionTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.car_b = self.make_car(self.dealer_b)
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)
        self.anon = APIClient()

    # 1 ───────────────────────────────────────────────────────────────────
    def test_1_anonymous_cannot_create_or_modify_cars(self):
        payload = car_payload(self.model, self.city)
        self.assertEqual(self.anon.post("/api/dashboard/cars/", payload, format="json").status_code, 401)
        self.assertEqual(self.anon.post("/api/cars/", payload, format="json").status_code, 401)
        url = f"/api/dashboard/cars/{self.car_b.pk}/"
        self.assertEqual(self.anon.patch(url, {"price": "1"}, format="json").status_code, 401)
        self.assertEqual(self.anon.delete(url).status_code, 401)
        self.assertEqual(self.anon.patch(f"/api/cars/{self.car_b.pk}/", {}, format="json").status_code, 401)
        self.assertEqual(self.anon.delete(f"/api/admin/cars/{self.car_b.pk}/").status_code, 401)
        self.assertEqual(Car.objects.count(), 1)

    def test_1b_authenticated_dealer_cannot_write_via_public_catalog(self):
        resp = self.client_a.post("/api/cars/", car_payload(self.model, self.city), format="json")
        self.assertEqual(resp.status_code, 403)

    # 2 ───────────────────────────────────────────────────────────────────
    def test_2_dealer_cannot_view_edit_or_delete_other_dealers_car(self):
        url = f"/api/dashboard/cars/{self.car_b.pk}/"
        self.assertEqual(self.client_a.get(url).status_code, 404)
        self.assertEqual(self.client_a.patch(url, {"price": "1.00"}, format="json").status_code, 404)
        self.assertEqual(self.client_a.delete(url).status_code, 404)
        self.car_b.refresh_from_db()
        self.assertEqual(str(self.car_b.price), "800000.00")

    def test_2b_dealer_list_contains_only_own_cars(self):
        own = self.make_car(self.dealer_a)
        resp = self.client_a.get("/api/dashboard/cars/")
        self.assertEqual(resp.status_code, 200)
        ids = {c["id"] for c in resp.data["results"]}
        self.assertEqual(ids, {str(own.pk)})

    # 3 ───────────────────────────────────────────────────────────────────
    def test_3_dealer_cannot_spoof_dealer_on_create(self):
        payload = car_payload(self.model, self.city, dealer=self.dealer_b.pk, dealer_id=self.dealer_b.pk)
        resp = self.client_a.post("/api/dashboard/cars/", payload, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        car = Car.objects.get(pk=resp.data["id"])
        self.assertEqual(car.dealer_id, self.dealer_a.pk)
        self.assertEqual(car.owner_id, self.manager_a.pk)

    def test_3b_dealer_cannot_move_own_car_to_other_dealer(self):
        own = self.make_car(self.dealer_a)
        resp = self.client_a.patch(
            f"/api/dashboard/cars/{own.pk}/", {"dealer": self.dealer_b.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        own.refresh_from_db()
        self.assertEqual(own.dealer_id, self.dealer_a.pk)

    # 4 ───────────────────────────────────────────────────────────────────
    def test_4_blocked_dealer_cannot_publish_or_edit(self):
        own = self.make_car(self.dealer_a)
        Dealer.objects.filter(pk=self.dealer_a.pk).update(is_active=False)
        self.manager_a.refresh_from_db()

        resp = self.client_a.post("/api/dashboard/cars/", car_payload(self.model, self.city), format="json")
        self.assertEqual(resp.status_code, 403)
        resp = self.client_a.patch(f"/api/dashboard/cars/{own.pk}/", {"price": "1"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.client_a.patch("/api/dashboard/dealer/", {"name": "x"}, format="json").status_code, 403)

    def test_4b_blocked_dealer_cars_hidden_from_public(self):
        own = self.make_car(self.dealer_a)
        Dealer.objects.filter(pk=self.dealer_a.pk).update(is_active=False)

        ids = {c["id"] for c in self.anon.get("/api/cars/").data["results"]}
        self.assertNotIn(str(own.pk), ids)
        self.assertIn(str(self.car_b.pk), ids)
        self.assertEqual(self.anon.get(f"/api/cars/{own.pk}/").status_code, 404)
        self.assertEqual(self.anon.get("/api/dealers/salon-a/").status_code, 404)
        slugs = {d["slug"] for d in self.anon.get("/api/dealers/").data}
        self.assertNotIn("salon-a", slugs)

    # 5 ───────────────────────────────────────────────────────────────────
    def test_5_dealer_cannot_access_admin_api(self):
        for url in (
            "/api/admin/dealers/",
            "/api/admin/managers/",
            "/api/admin/cars/",
            "/api/admin/stats/",
            "/api/admin/users/",
        ):
            self.assertEqual(self.client_a.get(url).status_code, 403, url)
        resp = self.client_a.post("/api/admin/dealers/", {"name": "Хак"}, format="json")
        self.assertEqual(resp.status_code, 403)
        resp = self.client_a.post(
            "/api/admin/managers/",
            {"email": "x@x.kg", "password": PASSWORD, "dealer": self.dealer_a.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        resp = self.client_a.patch(f"/api/admin/cars/{self.car_b.pk}/", {"status": "hidden"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # 6 ───────────────────────────────────────────────────────────────────
    def test_6_dealer_cannot_upload_into_other_dealers_folder(self):
        resp = self.client_a.post(
            "/api/dashboard/upload-signature/", {"folder": "cars/salon-b"}, format="json"
        )
        self.assertEqual(resp.status_code, 404)  # подписи не выдаются вовсе

        resp = self.client_a.post(
            f"/api/dashboard/cars/{self.car_b.pk}/photos/",
            {"images": [make_image()]},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(CarImage.objects.exists())
        self.assertFalse(os.path.exists(os.path.join(self.media_dir.name, "cars", "salon-b")))

    def test_6b_own_upload_goes_to_own_dealer_folder(self):
        own = self.make_car(self.dealer_a)
        resp = self.client_a.post(
            f"/api/dashboard/cars/{own.pk}/photos/", {"images": [make_image()]}, format="multipart"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertTrue(CarImage.objects.get().image.name.startswith("cars/salon-a/"))


class AuthRulesTests(MarketplaceTestCase):
    def test_public_registration_is_closed(self):
        resp = APIClient().post(
            "/api/auth/register/",
            {"email": "new@x.kg", "password": PASSWORD, "password_confirmation": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(User.objects.filter(email="new@x.kg").exists())

    def test_login_returns_jwt_and_me_returns_role_and_dealer(self):
        client = APIClient()
        resp = client.post("/api/auth/login/", {"email": "a@test.kg", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")
        me = client.get("/api/auth/me/").data
        self.assertEqual(me["role"], "dealer")
        self.assertEqual(me["dealer_slug"], "salon-a")
        self.assertTrue(me["dealer_is_active"])

    def test_login_is_throttled_after_5_attempts_per_minute(self):
        client = APIClient()
        codes = [
            client.post("/api/auth/login/", {"email": "a@test.kg", "password": "wrong"}, format="json").status_code
            for _ in range(6)
        ]
        self.assertEqual(codes[:5], [401] * 5)
        self.assertEqual(codes[5], 429)

    def test_disabled_manager_cannot_login(self):
        User.objects.filter(pk=self.manager_a.pk).update(is_active=False)
        resp = APIClient().post("/api/auth/login/", {"email": "a@test.kg", "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, 401)


class DealerDashboardTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.client_a = APIClient()
        self.client_a.force_authenticate(self.manager_a)

    def test_create_validates_price_year_and_defaults_phone(self):
        url = "/api/dashboard/cars/"
        self.assertEqual(self.client_a.post(url, car_payload(self.model, self.city, price="0"), format="json").status_code, 400)
        self.assertEqual(self.client_a.post(url, car_payload(self.model, self.city, year=1979), format="json").status_code, 400)
        self.assertEqual(self.client_a.post(url, car_payload(self.model, self.city, year=2100), format="json").status_code, 400)

        resp = self.client_a.post(url, car_payload(self.model, self.city, contact_phone=""), format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        car = Car.objects.get(pk=resp.data["id"])
        self.assertEqual(car.contact_phone, "+996700111111")
        self.assertEqual(car.status, Car.Status.ACTIVE)
        self.assertIsNotNone(car.published_at)

    def test_hide_sell_and_public_visibility(self):
        car = self.make_car(self.dealer_a)
        url = f"/api/dashboard/cars/{car.pk}/"
        anon = APIClient()
        self.assertEqual(anon.get(f"/api/cars/{car.pk}/").status_code, 200)

        self.assertEqual(self.client_a.patch(url, {"status": "hidden"}, format="json").status_code, 200)
        self.assertEqual(anon.get(f"/api/cars/{car.pk}/").status_code, 404)

        self.assertEqual(self.client_a.patch(url, {"status": "sold"}, format="json").status_code, 200)
        self.assertEqual(anon.get(f"/api/cars/{car.pk}/").status_code, 404)

        self.assertEqual(self.client_a.patch(url, {"status": "bogus"}, format="json").status_code, 400)

    def test_photos_limit_main_and_delete_removes_files(self):
        car = self.make_car(self.dealer_a)
        base = f"/api/dashboard/cars/{car.pk}/photos/"
        resp = self.client_a.post(base, {"images": [make_image(f"{i}.jpg") for i in range(3)]}, format="multipart")
        self.assertEqual(resp.status_code, 201, resp.data)
        photos = list(car.images.order_by("position"))
        self.assertTrue(photos[0].is_cover)
        self.assertIn("thumb", resp.data[0])

        resp = self.client_a.post(f"{base}{photos[2].pk}/main/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(car.images.get(is_cover=True).pk, photos[2].pk)

        path = photos[2].image.path
        self.assertTrue(os.path.exists(path))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client_a.delete(f"{base}{photos[2].pk}/").status_code, 204)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(car.images.filter(is_cover=True).count(), 1)

        resp = self.client_a.post(base, {"images": [make_image(f"x{i}.jpg") for i in range(14)]}, format="multipart")
        self.assertEqual(resp.status_code, 400)  # 2 + 14 > 15

    def test_photo_rejects_non_image_and_oversize(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        car = self.make_car(self.dealer_a)
        base = f"/api/dashboard/cars/{car.pk}/photos/"
        fake = SimpleUploadedFile("evil.jpg", b"<?php echo 1; ?>", content_type="image/jpeg")
        self.assertEqual(self.client_a.post(base, {"images": [fake]}, format="multipart").status_code, 400)
        big = SimpleUploadedFile("big.jpg", b"0" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        self.assertEqual(self.client_a.post(base, {"images": [big]}, format="multipart").status_code, 400)

    def test_delete_car_removes_photo_files(self):
        car = self.make_car(self.dealer_a)
        self.client_a.post(f"/api/dashboard/cars/{car.pk}/photos/", {"images": [make_image()]}, format="multipart")
        path = car.images.get().image.path
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client_a.delete(f"/api/dashboard/cars/{car.pk}/").status_code, 204)
        self.assertFalse(Car.objects.filter(pk=car.pk).exists())
        self.assertFalse(os.path.exists(path))

    def test_profile_edit_cannot_change_slug_or_active(self):
        resp = self.client_a.patch(
            "/api/dashboard/dealer/",
            {"name": "Новое имя", "slug": "hijack", "is_active": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.dealer_a.refresh_from_db()
        self.assertEqual(self.dealer_a.name, "Новое имя")
        self.assertEqual(self.dealer_a.slug, "salon-a")
        self.assertTrue(self.dealer_a.is_active)


class AdminApiTests(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        self.client_admin = APIClient()
        self.client_admin.force_authenticate(self.admin)

    def test_dealer_crud_and_toggle(self):
        # Без админа салона создать нельзя — и салон не создаётся
        resp = self.client_admin.post("/api/admin/dealers/", {"name": "Авто Лидер"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Dealer.objects.filter(name="Авто Лидер").exists())

        resp = self.client_admin.post(
            "/api/admin/dealers/",
            {"name": "Авто Лидер", "admin_email": "Boss@Lider.kg", "admin_password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["slug"], "avto-lider")
        self.assertNotIn("admin_password", resp.data)
        boss = User.objects.get(email="boss@lider.kg")
        self.assertEqual((boss.role, boss.dealer_id, boss.is_staff), ("dealer", resp.data["id"], False))
        self.assertEqual(resp.data["admin"]["email"], "boss@lider.kg")

        # Админ салона сразу входит в свою панель
        client = APIClient()
        login = client.post("/api/auth/login/", {"email": "boss@lider.kg", "password": PASSWORD}, format="json")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(client.get("/api/dashboard/dealer/").data["slug"], "avto-lider")
        self.assertEqual(client.get("/api/admin/dealers/").status_code, 403)
        dealer_id = resp.data["id"]
        resp = self.client_admin.patch(f"/api/admin/dealers/{dealer_id}/", {"is_active": False}, format="json")
        self.assertFalse(resp.data["is_active"])
        resp = self.client_admin.post(f"/api/admin/dealers/{dealer_id}/toggle_active/")
        self.assertTrue(resp.data["is_active"])
        self.assertEqual(self.client_admin.delete(f"/api/admin/dealers/{dealer_id}/").status_code, 204)

    def test_manager_create_reset_password_disable(self):
        resp = self.client_admin.post(
            "/api/admin/managers/",
            {"email": "New@Test.kg", "password": PASSWORD, "dealer": self.dealer_a.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        user = User.objects.get(email="new@test.kg")
        self.assertEqual(user.role, "dealer")
        self.assertFalse(user.is_staff)

        weak = self.client_admin.post(f"/api/admin/managers/{user.pk}/reset-password/", {"password": "123"}, format="json")
        self.assertEqual(weak.status_code, 400)
        resp = self.client_admin.post(
            f"/api/admin/managers/{user.pk}/reset-password/", {"password": "Another-strong-pass-77!"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Another-strong-pass-77!"))

        resp = self.client_admin.patch(f"/api/admin/managers/{user.pk}/", {"is_active": False}, format="json")
        self.assertFalse(resp.data["is_active"])

    def test_admin_cars_moderation_and_stats(self):
        car = self.make_car(self.dealer_b)
        resp = self.client_admin.patch(
            f"/api/admin/cars/{car.pk}/", {"status": "hidden", "dealer": self.dealer_a.pk}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        car.refresh_from_db()
        self.assertEqual((car.status, car.dealer_id), ("hidden", self.dealer_a.pk))

        stats = self.client_admin.get("/api/admin/stats/").data
        self.assertEqual(stats["dealers"]["total"], 2)
        self.assertEqual(stats["cars"]["hidden"], 1)
        by = {d["slug"]: d["total"] for d in stats["cars_by_dealer"]}
        self.assertEqual(by["salon-a"], 1)

        self.assertEqual(self.client_admin.delete(f"/api/admin/cars/{car.pk}/").status_code, 204)
        self.assertFalse(Car.objects.filter(pk=car.pk).exists())


class PublicCatalogTests(MarketplaceTestCase):
    def test_filters_and_dealer_info(self):
        self.make_car(self.dealer_a, year=2010, price="300000")
        new = self.make_car(self.dealer_b, year=2022, price="2000000", engine_type="hybrid")
        self.make_car(self.dealer_b, status=Car.Status.HIDDEN)
        anon = APIClient()

        data = anon.get("/api/cars/").data
        self.assertEqual(data["count"], 2)
        data = anon.get("/api/cars/", {"year_min": 2015, "price_max": 3000000, "fuel": "hybrid", "dealer": "salon-b"}).data
        self.assertEqual([c["id"] for c in data["results"]], [str(new.pk)])
        self.assertEqual(data["results"][0]["dealer_detail"]["name"], "Салон Б")

        ordered = anon.get("/api/cars/", {"ordering": "price"}).data["results"]
        self.assertEqual([c["price"] for c in ordered], ["300000.00", "2000000.00"])

        detail = anon.get("/api/dealers/salon-b/").data
        self.assertEqual(detail["dealer"]["car_count"], 1)
        self.assertEqual(len(detail["cars"]), 1)
