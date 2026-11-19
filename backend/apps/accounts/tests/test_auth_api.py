from io import BytesIO
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User


class AuthenticationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.media_dir = TemporaryDirectory()
        media_settings = override_settings(MEDIA_ROOT=self.media_dir.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.addCleanup(self.media_dir.cleanup)

        self.client = APIClient(enforce_csrf_checks=True)
        self.client.get("/api/auth/csrf/")
        self.csrf_token = self.client.cookies["csrftoken"].value
        self.csrf_headers = {"HTTP_X_CSRFTOKEN": self.csrf_token}
        self.password = "Strong-random-password-84!"

    def register_payload(self):
        return {
            "email": "buyer@example.com",
            "first_name": "Test",
            "last_name": "Buyer",
            "phone": "+996700123456",
            "password": self.password,
            "password_confirmation": self.password,
        }

    def test_local_frontend_origin_supports_credentialed_csrf_requests(self):
        frontend_origin = "http://127.0.0.1:5173"
        csrf = self.client.get(
            "/api/auth/csrf/",
            HTTP_ORIGIN=frontend_origin,
        )

        self.assertEqual(csrf.status_code, 200)
        self.assertEqual(
            csrf["Access-Control-Allow-Origin"],
            frontend_origin,
        )
        self.assertEqual(csrf["Access-Control-Allow-Credentials"], "true")

        User.objects.create_user(email="buyer@example.com", password=self.password)
        response = self.client.post(
            "/api/auth/login/",
            {"email": "buyer@example.com", "password": self.password},
            format="json",
            HTTP_ORIGIN=frontend_origin,
            **self.csrf_headers,
        )
        self.assertEqual(response.status_code, 200)

    def test_login_refresh_and_logout(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            first_name="Test",
            last_name="Buyer",
            phone="+996700123456",
        )
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))

        login = self.client.post(
            "/api/auth/login/",
            {"email": "buyer@example.com", "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)
        self.assertNotIn("refresh", login.data)
        access = login.data["access"]
        old_refresh = login.cookies["autokg_refresh"].value

        refresh = self.client.post(
            "/api/auth/refresh/",
            {},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(refresh.status_code, 200)
        self.assertIn("access", refresh.data)
        self.assertNotIn("refresh", refresh.data)
        rotated_refresh = refresh.cookies["autokg_refresh"].value
        self.assertNotEqual(rotated_refresh, old_refresh)

        self.client.cookies["autokg_refresh"] = old_refresh
        replay = self.client.post(
            "/api/auth/refresh/",
            {},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(replay.status_code, 401)
        self.client.cookies["autokg_refresh"] = rotated_refresh

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "buyer@example.com")

        logout = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(logout.cookies["autokg_refresh"].value, "")

    def test_refresh_throttle_allows_multiple_session_restores(self):
        User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            phone="+996700123456",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": "buyer@example.com", "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(login.status_code, 200)

        for attempt in range(6):
            with self.subTest(refresh_attempt=attempt + 1):
                refresh = self.client.post(
                    "/api/auth/refresh/",
                    {},
                    format="json",
                    **self.csrf_headers,
                )
                self.assertEqual(refresh.status_code, 200)
                self.assertIn("access", refresh.data)

    def test_invalid_login_does_not_issue_tokens(self):
        User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            phone="+996700123456",
        )

        response = self.client.post(
            "/api/auth/login/",
            {"email": "buyer@example.com", "password": "wrong-password"},
            format="json",
            **self.csrf_headers,
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("access", response.data)
        self.assertNotIn("autokg_refresh", response.cookies)

    def test_profile_patch_cannot_change_email_or_role(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            phone="+996700123456",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )

        response = self.client.patch(
            "/api/auth/profile/",
            {
                "first_name": "Updated",
                "email": "attacker@example.com",
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Updated")
        self.assertEqual(user.email, "buyer@example.com")
        self.assertEqual(user.role, User.Role.USER)

    def test_profile_photo_upload_validation_and_removal(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            phone="+996700123456",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )

        image_buffer = BytesIO()
        Image.new("RGB", (16, 16), color=(30, 90, 150)).save(
            image_buffer,
            format="JPEG",
        )
        photo = SimpleUploadedFile(
            "avatar.jpg",
            image_buffer.getvalue(),
            content_type="image/jpeg",
        )
        uploaded = self.client.patch(
            "/api/auth/profile/",
            {"profile_photo": photo},
            format="multipart",
        )

        self.assertEqual(uploaded.status_code, 200)
        self.assertTrue(uploaded.data["profile_photo"].endswith(".jpg"))
        user.refresh_from_db()
        first_photo = user.profile_photo
        self.assertTrue(first_photo.storage.exists(first_photo.name))

        png_buffer = BytesIO()
        Image.new("RGB", (18, 18), color=(150, 90, 30)).save(
            png_buffer,
            format="PNG",
        )
        replacement_photo = SimpleUploadedFile(
            "avatar.png",
            png_buffer.getvalue(),
            content_type="image/png",
        )
        replaced = self.client.patch(
            "/api/auth/profile/",
            {"profile_photo": replacement_photo},
            format="multipart",
        )
        self.assertEqual(replaced.status_code, 200)
        user.refresh_from_db()
        active_photo = user.profile_photo
        self.assertTrue(active_photo.name.endswith(".png"))
        self.assertFalse(first_photo.storage.exists(first_photo.name))
        self.assertTrue(active_photo.storage.exists(active_photo.name))

        invalid_photo = SimpleUploadedFile(
            "avatar.txt",
            image_buffer.getvalue(),
            content_type="image/jpeg",
        )
        invalid = self.client.patch(
            "/api/auth/profile/",
            {"profile_photo": invalid_photo},
            format="multipart",
        )
        self.assertEqual(invalid.status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.profile_photo.name, active_photo.name)

        removed = self.client.patch(
            "/api/auth/profile/",
            {"profile_photo": None},
            format="json",
        )
        self.assertEqual(removed.status_code, 200)
        self.assertIsNone(removed.data["profile_photo"])
        self.assertFalse(active_photo.storage.exists(active_photo.name))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_password_reset_sends_single_use_link_and_revokes_old_tokens(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            first_name="Test",
            last_name="Buyer",
            phone="+996700123456",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        old_access = login.data["access"]
        old_refresh = login.cookies["autokg_refresh"].value

        reset_request = self.client.post(
            "/api/auth/password-reset/",
            {"email": user.email},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(reset_request.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        reset_url = mail.outbox[0].body.splitlines()[-1]
        reset_params = parse_qs(urlsplit(reset_url).query)
        reset = self.client.post(
            "/api/auth/password-reset/confirm/",
            {
                "uid": reset_params["uid"][0],
                "token": reset_params["token"][0],
                "new_password": "Different-secure-password-37$",
                "new_password_confirmation": "Different-secure-password-37$",
            },
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(reset.status_code, 200)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {old_access}")
        old_access_response = self.client.get("/api/auth/me/")
        self.assertEqual(old_access_response.status_code, 401)

        self.client.credentials()
        self.client.cookies["autokg_refresh"] = old_refresh
        old_refresh_response = self.client.post(
            "/api/auth/refresh/",
            {},
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(old_refresh_response.status_code, 401)

        new_login = self.client.post(
            "/api/auth/login/",
            {
                "email": user.email,
                "password": "Different-secure-password-37$",
            },
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(new_login.status_code, 200)

    def test_password_change_checks_current_password_and_revokes_session(self):
        user = User.objects.create_user(
            email="buyer@example.com",
            password=self.password,
            phone="+996700123456",
        )
        login = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": self.password},
            format="json",
            **self.csrf_headers,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['access']}"
        )
        payload = {
            "current_password": "wrong-current-password",
            "new_password": "Different-secure-password-37$",
            "new_password_confirmation": "Different-secure-password-37$",
        }

        invalid = self.client.post(
            "/api/auth/password-change/",
            payload,
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(invalid.status_code, 400)

        payload["current_password"] = self.password
        changed = self.client.post(
            "/api/auth/password-change/",
            payload,
            format="json",
            **self.csrf_headers,
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.cookies["autokg_refresh"].value, "")

        old_access_response = self.client.get("/api/auth/me/")
        self.assertEqual(old_access_response.status_code, 401)
