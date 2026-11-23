from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ads.models import AdBanner, AdDailyStat
from apps.common.testing import MarketplaceTestCase, make_image


class AdTestCase(MarketplaceTestCase):
    client_class = APIClient

    def make_banner(self, **overrides):
        fields = {
            "title": "Автокредит от 14%",
            "advertiser": "Банк Тест",
            "placement": AdBanner.Placement.HOME_TOP,
            "image": make_image("ad.jpg"),
            "link_url": "https://bank.example.kg/credit",
        }
        fields.update(overrides)
        return AdBanner.objects.create(**fields)


class PublicAdTests(AdTestCase):
    def test_list_shows_only_live_banners_without_link(self):
        today = timezone.localdate()
        live = self.make_banner()
        self.make_banner(title="выключен", is_active=False)
        self.make_banner(title="ещё не начался", starts_on=today + timedelta(days=1))
        self.make_banner(title="закончился", ends_on=today - timedelta(days=1))
        self.make_banner(title="последний день", ends_on=today)

        response = self.client.get("/api/ads/")
        self.assertEqual(response.status_code, 200)
        titles = {item["title"] for item in response.data}
        self.assertEqual(titles, {live.title, "последний день"})
        self.assertNotIn("link_url", response.data[0])
        self.assertTrue(response.data[0]["image_url"])

    def test_list_returns_at_most_three_banners_per_placement(self):
        for priority in (1, 2, 3, 4):
            self.make_banner(title=f"p{priority}", priority=priority)
        self.make_banner(title="другое место", placement=AdBanner.Placement.CAR_DETAIL)
        titles = [item["title"] for item in self.client.get("/api/ads/").data]
        self.assertEqual(sorted(titles), sorted(["p4", "p3", "p2", "другое место"]))

    def test_impressions_count_only_live_banners(self):
        live = self.make_banner()
        off = self.make_banner(is_active=False)
        response = self.client.post("/api/ads/impressions/", {"ids": [live.pk, off.pk, live.pk]}, format="json")
        self.assertEqual(response.status_code, 204)
        live.refresh_from_db()
        off.refresh_from_db()
        self.assertEqual((live.impressions, off.impressions), (1, 0))
        self.client.post("/api/ads/impressions/", {"ids": [live.pk]}, format="json")
        stat = AdDailyStat.objects.get(banner=live, date=timezone.localdate())
        self.assertEqual(stat.impressions, 2)

    def test_impressions_validates_payload(self):
        self.assertEqual(self.client.post("/api/ads/impressions/", {"ids": []}, format="json").status_code, 400)
        too_many = {"ids": list(range(1, 20))}
        self.assertEqual(self.client.post("/api/ads/impressions/", too_many, format="json").status_code, 400)

    def test_click_redirects_and_counts_once_per_visitor(self):
        banner = self.make_banner()
        response = self.client.get(f"/api/ads/{banner.pk}/click/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], banner.link_url)
        self.client.get(f"/api/ads/{banner.pk}/click/")
        banner.refresh_from_db()
        self.assertEqual(banner.clicks, 1)
        self.assertEqual(AdDailyStat.objects.get(banner=banner).clicks, 1)

        cache.clear()
        self.client.get(f"/api/ads/{banner.pk}/click/")
        banner.refresh_from_db()
        self.assertEqual(banner.clicks, 2)

    def test_click_on_finished_banner_redirects_without_counting(self):
        banner = self.make_banner(ends_on=timezone.localdate() - timedelta(days=1))
        response = self.client.get(f"/api/ads/{banner.pk}/click/")
        self.assertEqual(response.status_code, 302)
        banner.refresh_from_db()
        self.assertEqual(banner.clicks, 0)


class AdminAdTests(AdTestCase):
    url = "/api/admin/ads/"

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return response.data["error"]["details"]

    def payload(self, **overrides):
        data = {
            "title": "КАСКО за 1 день",
            "advertiser": "Страховая Тест",
            "placement": "catalog_feed",
            "link_url": "https://insurance.example.kg",
            "image": make_image("banner.png", fmt="PNG"),
        }
        data.update(overrides)
        return data

    def test_only_admin_can_manage_ads(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.client.force_authenticate(self.manager_a)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_admin_creates_updates_and_deletes_banner(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(self.url, self.payload(), format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        banner_id = response.data["id"]
        self.assertTrue(response.data["is_live"])
        self.assertEqual(response.data["placement_label"], "Каталог — в списке объявлений")

        response = self.client.patch(f"{self.url}{banner_id}/", {"is_active": False}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_live"])

        self.assertEqual(self.client.delete(f"{self.url}{banner_id}/").status_code, 204)
        self.assertFalse(AdBanner.objects.exists())

    def test_create_requires_image_and_valid_link_and_period(self):
        self.client.force_authenticate(self.admin)
        data = self.payload()
        data.pop("image")
        self.assertIn("image", self.errors(self.client.post(self.url, data, format="multipart")))
        bad_link = self.payload(link_url="javascript:alert(1)")
        self.assertIn("link_url", self.errors(self.client.post(self.url, bad_link, format="multipart")))
        bad_period = self.payload(starts_on="2026-05-10", ends_on="2026-05-01")
        self.assertIn("ends_on", self.errors(self.client.post(self.url, bad_period, format="multipart")))

    def test_max_three_active_banners_per_placement(self):
        self.client.force_authenticate(self.admin)
        today = timezone.localdate()
        for _ in range(3):
            self.make_banner(placement="catalog_feed")
        self.make_banner(placement="catalog_feed", is_active=False)
        self.make_banner(placement="catalog_feed", ends_on=today - timedelta(days=1))
        self.assertIn("placement", self.errors(self.client.post(self.url, self.payload(), format="multipart")))
        # выключенный баннер и другое место — можно
        off = self.client.post(self.url, self.payload(is_active=False), format="multipart")
        self.assertEqual(off.status_code, 201, off.data)
        self.assertIn("placement", self.errors(
            self.client.patch(f"{self.url}{off.data['id']}/", {"is_active": True}, format="multipart")
        ))
        other = self.client.post(self.url, self.payload(placement="home_top"), format="multipart")
        self.assertEqual(other.status_code, 201, other.data)
        # период, который начинается после окончания занятых, — тоже можно
        later = today + timedelta(days=40)
        for banner in AdBanner.objects.filter(placement="catalog_feed", is_active=True, ends_on__isnull=True):
            banner.ends_on = today + timedelta(days=30)
            banner.save(update_fields=["ends_on"])
        future = self.client.post(self.url, self.payload(starts_on=later.isoformat()), format="multipart")
        self.assertEqual(future.status_code, 201, future.data)

    def test_remove_mobile_image(self):
        banner = self.make_banner(mobile_image=make_image("m.jpg"))
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"{self.url}{banner.pk}/", {"remove_mobile_image": True}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["mobile_image_url"])

    def test_stats_and_excel_export(self):
        banner = self.make_banner(starts_on=timezone.localdate() - timedelta(days=5))
        today = timezone.localdate()
        AdDailyStat.objects.create(banner=banner, date=today - timedelta(days=1), impressions=200, clicks=4)
        AdDailyStat.objects.create(banner=banner, date=today, impressions=100, clicks=2)
        self.client.force_authenticate(self.admin)

        data = self.client.get(f"{self.url}{banner.pk}/stats/").data
        self.assertEqual(data["totals"], {"impressions": 300, "clicks": 6, "ctr": 2.0})
        self.assertEqual(len(data["days"]), 2)

        response = self.client.get(f"{self.url}{banner.pk}/stats/export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])

        bad = self.client.get(f"{self.url}{banner.pk}/stats/?from=2026-02-10&to=2026-02-01")
        self.assertEqual(bad.status_code, 400)


class AdPricingTests(AdTestCase):
    prices_url = "/api/admin/ad-prices/"

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.admin)

    def test_prices_list_has_all_placements(self):
        response = self.client.get(self.prices_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["placement"] for row in response.data], list(AdBanner.Placement.values))
        self.assertEqual(response.data[0]["price_week"], "0.00")

    def test_admin_updates_prices(self):
        response = self.client.put(
            self.prices_url,
            [
                {"placement": "home_top", "price_week": "5000", "price_month": "15000"},
                {"placement": "car_detail", "price_week": "2000", "price_month": "6000"},
            ],
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        prices = {row["placement"]: row for row in response.data}
        self.assertEqual(prices["home_top"]["price_month"], "15000.00")
        self.assertEqual(prices["car_detail"]["price_week"], "2000.00")
        self.assertEqual(prices["home_middle"]["price_week"], "0.00")

    def test_negative_or_unknown_rejected(self):
        bad = self.client.put(self.prices_url, [{"placement": "home_top", "price_week": "-1", "price_month": "1"}], format="json")
        self.assertEqual(bad.status_code, 400)
        unknown = self.client.put(self.prices_url, [{"placement": "nope", "price_week": "1", "price_month": "1"}], format="json")
        self.assertEqual(unknown.status_code, 400)

    def test_dealer_cannot_see_prices(self):
        self.client.force_authenticate(self.manager_a)
        self.assertEqual(self.client.get(self.prices_url).status_code, 403)

    def test_banner_price_and_paid_flag(self):
        banner = self.make_banner()
        response = self.client.patch(f"/api/admin/ads/{banner.pk}/", {"price": "12000", "is_paid": "true"}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["price"], response.data["is_paid"]), ("12000.00", True))
        response = self.client.patch(f"/api/admin/ads/{banner.pk}/", {"price": ""}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["price"])
