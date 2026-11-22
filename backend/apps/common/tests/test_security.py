from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User


LOGIN_URL = "/api/auth/login/"


def attempt(client, email="victim@test.kg", **extra):
    return client.post(LOGIN_URL, {"email": email, "password": "wrong-password"}, format="json", **extra).status_code


class SpoofedForwardedForTests(TestCase):
    """Подменой X-Forwarded-For нельзя обойти лимит попыток входа."""

    def setUp(self):
        cache.clear()

    @override_settings(CLIENT_IP_HEADER="CF-Connecting-IP")
    def test_random_forwarded_for_does_not_reset_ip_limit(self):
        client = APIClient()
        codes = [
            attempt(
                client,
                email=f"user{i}@test.kg",
                HTTP_CF_CONNECTING_IP="203.0.113.7",
                HTTP_X_FORWARDED_FOR=f"10.0.0.{i}",
            )
            for i in range(6)
        ]
        self.assertEqual(codes[:5], [401] * 5)
        self.assertEqual(codes[5], 429)

    @override_settings(CLIENT_IP_HEADER="CF-Connecting-IP")
    def test_different_real_ips_have_separate_limits(self):
        client = APIClient()
        for i in range(5):
            attempt(client, email=f"a{i}@test.kg", HTTP_CF_CONNECTING_IP="203.0.113.7")
        self.assertEqual(attempt(client, email="b@test.kg", HTTP_CF_CONNECTING_IP="198.51.100.9"), 401)


class LoginAccountThrottleTests(TestCase):
    """Подбор пароля к одному аккаунту с разных IP упирается в лимит аккаунта."""

    def setUp(self):
        cache.clear()
        User.objects.create_user(email="victim@test.kg", password="Strong-random-password-84!")

    @override_settings(CLIENT_IP_HEADER="CF-Connecting-IP")
    def test_many_ips_hit_account_limit(self):
        client = APIClient()
        codes = [
            attempt(client, email="Victim@Test.kg ", HTTP_CF_CONNECTING_IP=f"203.0.113.{i}")
            for i in range(21)
        ]
        self.assertEqual(codes[:20], [401] * 20)
        self.assertEqual(codes[20], 429)
