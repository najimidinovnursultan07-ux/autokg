from django.test import TestCase
from rest_framework.test import APIClient


class HealthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_liveness_is_public(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    def test_readiness_checks_database(self):
        response = self.client.get("/api/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ready", "database": "ok"})
