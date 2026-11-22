import re
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import LoginChallenge, User


PASSWORD = "Strong-random-password-84!"
TELEGRAM = {"TELEGRAM_BOT_TOKEN": "test-token", "TELEGRAM_ADMIN_CHAT_ID": "42", "ADMIN_2FA_ENABLED": True}
SEND = "apps.subscriptions.notifications.send_telegram"


def sent_code(mock_send):
    return re.search(r"\b(\d{6})\b", mock_send.call_args[0][0]).group(1)


@override_settings(**TELEGRAM)
class AdminTwoFactorApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            email="admin@test.kg", password=PASSWORD, role=User.Role.ADMIN, is_staff=True
        )
        self.dealer = User.objects.create_user(email="dealer@test.kg", password=PASSWORD, role=User.Role.DEALER)
        self.client = APIClient()

    def login(self, email="admin@test.kg", password=PASSWORD):
        return self.client.post("/api/auth/login/", {"email": email, "password": password}, format="json")

    def verify(self, challenge_id, code):
        return self.client.post("/api/auth/login/verify/", {"challenge_id": challenge_id, "code": code}, format="json")

    @patch(SEND, return_value=True)
    def test_admin_gets_no_tokens_until_code_is_entered(self, mock_send):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["two_factor_required"])
        self.assertNotIn("access", resp.data)
        self.assertNotIn("autobuy_refresh", resp.cookies)

        resp = self.verify(resp.data["challenge_id"], sent_code(mock_send))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("autobuy_refresh", resp.cookies)

    @patch(SEND, return_value=True)
    def test_code_is_single_use(self, mock_send):
        challenge_id = self.login().data["challenge_id"]
        code = sent_code(mock_send)
        self.assertEqual(self.verify(challenge_id, code).status_code, 200)
        self.assertEqual(self.verify(challenge_id, code).status_code, 400)

    @patch(SEND, return_value=True)
    def test_five_wrong_codes_burn_the_challenge(self, mock_send):
        challenge_id = self.login().data["challenge_id"]
        code = sent_code(mock_send)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.assertEqual(self.verify(challenge_id, wrong).status_code, 400)
        self.assertEqual(self.verify(challenge_id, code).status_code, 400)

    @patch(SEND, return_value=True)
    def test_expired_code_rejected(self, mock_send):
        challenge_id = self.login().data["challenge_id"]
        LoginChallenge.objects.filter(pk=challenge_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.verify(challenge_id, sent_code(mock_send)).status_code, 400)

    @patch(SEND, return_value=True)
    def test_new_login_cancels_previous_code(self, mock_send):
        first_id = self.login().data["challenge_id"]
        first_code = sent_code(mock_send)
        self.login()
        self.assertEqual(self.verify(first_id, first_code).status_code, 400)

    @patch(SEND, return_value=True)
    def test_wrong_password_sends_nothing(self, mock_send):
        self.assertEqual(self.login(password="wrong-password").status_code, 401)
        mock_send.assert_not_called()

    @patch(SEND, return_value=False)
    def test_telegram_failure_returns_503(self, mock_send):
        self.assertEqual(self.login().status_code, 503)
        self.assertFalse(LoginChallenge.objects.exists())

    @patch(SEND, return_value=True)
    def test_dealer_logs_in_without_code(self, mock_send):
        resp = self.login(email="dealer@test.kg")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        mock_send.assert_not_called()

    @override_settings(TELEGRAM_BOT_ADMIN_TOKEN="admin-bot", TELEGRAM_ADMIN_2FA_CHAT_ID="777")
    @patch(SEND, return_value=True)
    def test_separate_admin_bot_is_used(self, mock_send):
        self.login()
        self.assertEqual(mock_send.call_args[0][1:], ("admin-bot", "777"))

    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_BOT_ADMIN_TOKEN="admin-bot")
    @patch(SEND, return_value=True)
    def test_admin_bot_alone_enables_2fa(self, mock_send):
        self.assertTrue(self.login().data["two_factor_required"])
        self.assertEqual(mock_send.call_args[0][1:], ("admin-bot", "42"))

    @override_settings(ADMIN_2FA_ENABLED=False)
    @patch(SEND, return_value=True)
    def test_can_be_disabled(self, mock_send):
        self.assertIn("access", self.login().data)
        mock_send.assert_not_called()


@override_settings(
    **TELEGRAM,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class AdminSiteTwoFactorTests(TestCase):
    def setUp(self):
        cache.clear()
        User.objects.create_user(email="admin@test.kg", password=PASSWORD, role=User.Role.ADMIN, is_staff=True)
        self.client = Client()

    @patch(SEND, return_value=True)
    def test_django_admin_requires_code(self, mock_send):
        resp = self.client.post("/django-admin/login/", {"username": "admin@test.kg", "password": PASSWORD})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "admin/two_factor_code.html")
        self.assertEqual(self.client.get("/django-admin/").status_code, 302)

        resp = self.client.post("/django-admin/login/", {"code": sent_code(mock_send)})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.get("/django-admin/").status_code, 200)

    @patch(SEND, return_value=True)
    def test_session_login_without_code_has_no_access(self, mock_send):
        self.client.login(username="admin@test.kg", password=PASSWORD)
        self.assertEqual(self.client.get("/django-admin/").status_code, 302)


class PasswordResetMailFailureTests(TestCase):
    """Почта упала: ответ такой же, как для несуществующего email, админу — сигнал в Telegram."""

    def setUp(self):
        cache.clear()
        User.objects.create_user(email="dealer@test.kg", password=PASSWORD, role=User.Role.DEALER)

    @patch(SEND, return_value=True)
    @patch("apps.accounts.views.send_mail", side_effect=OSError("Network is unreachable"))
    def test_smtp_failure_returns_same_answer_and_alerts_admin(self, _mail, mock_telegram):
        client = APIClient()
        existing = client.post("/api/auth/password-reset/", {"email": "dealer@test.kg"}, format="json")
        missing = client.post("/api/auth/password-reset/", {"email": "nobody@test.kg"}, format="json")
        self.assertEqual(existing.status_code, 200)
        self.assertEqual(existing.data, missing.data)
        mock_telegram.assert_called_once()
        self.assertIn("dealer@test.kg", mock_telegram.call_args[0][0])


class AdminEmailChangeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user(
            email="admin@test.kg", password=PASSWORD, role=User.Role.ADMIN, is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def change(self, **data):
        return self.client.post("/api/auth/email-change/", data, format="json")

    @patch(SEND, return_value=True)
    def test_admin_changes_email_with_password(self, mock_telegram):
        from django.core import mail

        resp = self.change(current_password=PASSWORD, new_email="New.Admin@Gmail.com")
        self.assertEqual(resp.status_code, 200, resp.data)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, "new.admin@gmail.com")
        self.assertEqual(mail.outbox[0].to, ["admin@test.kg"])
        mock_telegram.assert_called_once()
        login = APIClient().post("/api/auth/login/", {"email": "new.admin@gmail.com", "password": PASSWORD}, format="json")
        self.assertEqual(login.status_code, 200)

    def test_wrong_password_rejected(self):
        self.assertEqual(self.change(current_password="wrong", new_email="x@gmail.com").status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, "admin@test.kg")

    def test_taken_email_rejected(self):
        User.objects.create_user(email="taken@test.kg", password=PASSWORD)
        self.assertEqual(self.change(current_password=PASSWORD, new_email="TAKEN@test.kg").status_code, 400)

    def test_dealer_cannot_change_email(self):
        dealer = User.objects.create_user(email="d@test.kg", password=PASSWORD, role=User.Role.DEALER)
        client = APIClient()
        client.force_authenticate(dealer)
        resp = client.post("/api/auth/email-change/", {"current_password": PASSWORD, "new_email": "z@gmail.com"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_change_password(self):
        resp = self.client.post(
            "/api/auth/password-change/",
            {"current_password": PASSWORD, "new_password": "Another-strong-pass-91!", "new_password_confirmation": "Another-strong-pass-91!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
