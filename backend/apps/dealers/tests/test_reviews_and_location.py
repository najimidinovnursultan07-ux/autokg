from django.core.cache import cache
from rest_framework.test import APIClient

from apps.common.testing import MarketplaceTestCase
from apps.dealers.models import DealerReview


class DealerReviewTests(MarketplaceTestCase):
    client_class = APIClient

    def setUp(self):
        super().setUp()
        cache.clear()
        self.url = f"/api/dealers/{self.dealer_a.slug}/reviews/"
        self.payload = {"author_name": "Азамат", "rating": 5, "text": "Отличный салон, всё честно и быстро."}

    def test_new_review_is_pending_and_hidden_until_published(self):
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201)
        review = DealerReview.objects.get()
        self.assertEqual(review.status, DealerReview.Status.PENDING)
        self.assertEqual(self.client.get(self.url).data["count"], 0)

        review.status = DealerReview.Status.PUBLISHED
        review.save()
        listing = self.client.get(self.url).data
        self.assertEqual(listing["count"], 1)
        self.assertEqual(set(listing["results"][0]), {"id", "author_name", "rating", "text", "created_at"})

    def test_rating_counts_only_published_reviews(self):
        DealerReview.objects.create(dealer=self.dealer_a, author_name="A", rating=5, text="x" * 10, status="published")
        DealerReview.objects.create(dealer=self.dealer_a, author_name="B", rating=4, text="x" * 10, status="published")
        DealerReview.objects.create(dealer=self.dealer_a, author_name="C", rating=1, text="x" * 10, status="pending")
        self.make_car(self.dealer_a)
        self.make_car(self.dealer_a)  # несколько машин не должны искажать рейтинг

        dealers = {d["slug"]: d for d in self.client.get("/api/dealers/").data}
        self.assertEqual(dealers["salon-a"]["rating"], 4.5)
        self.assertEqual(dealers["salon-a"]["reviews_count"], 2)
        self.assertEqual(dealers["salon-a"]["car_count"], 2)
        self.assertIsNone(dealers["salon-b"]["rating"])
        self.assertEqual(dealers["salon-b"]["reviews_count"], 0)
        detail = self.client.get(f"/api/dealers/{self.dealer_a.slug}/").data["dealer"]
        self.assertEqual((detail["rating"], detail["reviews_count"]), (4.5, 2))

    def test_validation(self):
        for bad in ({"rating": 6}, {"rating": 0}, {"text": "коротко"}, {"author_name": " "}):
            response = self.client.post(self.url, {**self.payload, **bad}, format="json")
            self.assertEqual(response.status_code, 400, bad)
        self.assertFalse(DealerReview.objects.exists())

    def test_honeypot_silently_drops_bot_reviews(self):
        response = self.client.post(self.url, {**self.payload, "website": "http://spam"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertFalse(DealerReview.objects.exists())

    def test_review_rate_limit(self):
        codes = [self.client.post(self.url, self.payload, format="json").status_code for _ in range(6)]
        self.assertEqual(codes[:5], [201] * 5)
        self.assertEqual(codes[5], 429)

    def test_admin_moderation_and_permissions(self):
        review = DealerReview.objects.create(dealer=self.dealer_a, author_name="A", rating=3, text="x" * 10)
        url = f"/api/admin/reviews/{review.pk}/"

        self.client.force_authenticate(self.manager_a)
        self.assertEqual(self.client.patch(url, {"status": "published"}, format="json").status_code, 403)

        self.client.force_authenticate(self.admin)
        pending = self.client.get("/api/admin/reviews/", {"status": "pending"}).data
        self.assertEqual(pending["count"], 1)
        self.assertEqual(pending["results"][0]["dealer_name"], self.dealer_a.name)
        response = self.client.patch(url, {"status": "published", "rating": 5}, format="json")
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual((review.status, review.rating), ("published", 3))  # оценку админ не меняет
        self.assertEqual(self.client.delete(url).status_code, 204)


class DealerLocationTests(MarketplaceTestCase):
    client_class = APIClient

    def test_manager_sets_location_and_it_is_public(self):
        self.client.force_authenticate(self.manager_a)
        response = self.client.patch(
            "/api/dashboard/dealer/", {"latitude": "42.874621", "longitude": "74.569762"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        public = self.client.get(f"/api/dealers/{self.dealer_a.slug}/").data["dealer"]
        self.assertEqual((public["latitude"], public["longitude"]), ("42.874621", "74.569762"))

    def test_location_requires_both_coordinates_and_valid_range(self):
        self.client.force_authenticate(self.manager_a)
        only_lat = self.client.patch("/api/dashboard/dealer/", {"latitude": "42.87"}, format="json")
        self.assertEqual(only_lat.status_code, 400)
        out_of_range = self.client.patch(
            "/api/dashboard/dealer/", {"latitude": "142", "longitude": "74.5"}, format="json"
        )
        self.assertEqual(out_of_range.status_code, 400)

    def test_location_can_be_cleared_from_form_data(self):
        self.dealer_a.latitude, self.dealer_a.longitude = 42.87, 74.56
        self.dealer_a.save()
        self.client.force_authenticate(self.manager_a)
        response = self.client.patch(
            "/api/dashboard/dealer/", {"latitude": "", "longitude": ""}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.dealer_a.refresh_from_db()
        self.assertIsNone(self.dealer_a.latitude)
