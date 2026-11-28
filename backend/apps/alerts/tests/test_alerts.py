from datetime import timedelta
from unittest.mock import patch

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.alerts import telegram
from apps.alerts.models import PriceWatch, SavedSearch, TelegramChat
from apps.alerts.services import run_alerts
from apps.cars.models import Car, Model
from apps.common.testing import MarketplaceTestCase
from apps.subscriptions.models import Plan
from apps.subscriptions.services import activate_subscription

BOT = dict(
    TELEGRAM_ALERTS_BOT_TOKEN="123:abc",
    TELEGRAM_ALERTS_BOT_USERNAME="autobuy_alerts_bot",
    FRONTEND_URL="https://autobuy.test",
    CRON_SECRET="cron",
)
CHAT_ID = 555


@override_settings(**BOT)
class AlertsTestCase(MarketplaceTestCase):
    def setUp(self):
        super().setUp()
        activate_subscription(self.dealer_a, Plan.objects.get(code="business"), 1, amount="2100", payment_method="cash")
        self.client = APIClient()
        self.sent = []
        patcher = patch("apps.alerts.telegram.call", side_effect=self.fake_call)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_call(self, method, payload):
        self.sent.append((method, payload))
        return {"message_id": 1}

    def messages(self):
        return [p["text"] for m, p in self.sent if m == "sendMessage"]

    def webhook(self, update, secret=None):
        return self.client.post(
            "/api/alerts/telegram/webhook/", update, format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret or telegram.webhook_secret(),
        )

    def start(self, payload):
        return self.webhook({"message": {
            "chat": {"id": CHAT_ID}, "from": {"username": "buyer", "first_name": "Айбек"},
            "text": f"/start {payload}",
        }})

    def subscribe_search(self, filters, title="Toyota Camry"):
        resp = self.client.post("/api/alerts/searches/", {"filters": filters, "title": title}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        payload = resp.data["bot_url"].split("?start=")[1]
        self.start(payload)
        return SavedSearch.objects.get(token=payload[2:])


class SubscribeTests(AlertsTestCase):
    def test_search_link_and_start_binds_chat(self):
        resp = self.client.post(
            "/api/alerts/searches/",
            {"filters": {"brand": self.brand.id, "price_max": "1500000", "bogus": "x"}, "title": "Toyota до 1,5 млн"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["bot_url"].startswith("https://t.me/autobuy_alerts_bot?start=s_"))
        search = SavedSearch.objects.get()
        self.assertEqual(search.filters, {"brand": str(self.brand.id), "price_max": "1500000"})
        self.assertIsNone(search.chat)

        self.start(f"s_{search.token}")
        search.refresh_from_db()
        self.assertEqual(search.chat.chat_id, CHAT_ID)
        self.assertIsNotNone(search.subscribed_at)
        self.assertIn("Подписка оформлена", self.messages()[-1])

    def test_invalid_filters_rejected(self):
        resp = self.client.post("/api/alerts/searches/", {"filters": {"price_max": "дорого"}}, format="json")
        self.assertEqual(resp.status_code, 400)

    @override_settings(TELEGRAM_ALERTS_BOT_TOKEN="")
    def test_not_configured(self):
        resp = self.client.post("/api/alerts/searches/", {"filters": {}}, format="json")
        self.assertEqual(resp.status_code, 503)

    def test_webhook_rejects_wrong_secret(self):
        resp = self.webhook({"message": {"chat": {"id": 1}, "text": "/start"}}, secret="wrong")
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(TelegramChat.objects.exists())

    def test_link_cannot_be_claimed_by_another_chat(self):
        search = self.subscribe_search({})
        self.webhook({"message": {"chat": {"id": 999}, "text": f"/start s_{search.token}"}})
        search.refresh_from_db()
        self.assertEqual(search.chat.chat_id, CHAT_ID)
        self.assertIn("уже использована", self.messages()[-1])

    def test_price_watch_only_for_public_car(self):
        car = self.make_car(self.dealer_a)
        hidden = self.make_car(self.dealer_a, status=Car.Status.HIDDEN)
        ok = self.client.post("/api/alerts/watches/", {"car": str(car.id)}, format="json")
        self.assertEqual(ok.status_code, 201)
        self.assertIn("?start=w_", ok.data["bot_url"])
        missing = self.client.post("/api/alerts/watches/", {"car": str(hidden.id)}, format="json")
        self.assertEqual(missing.status_code, 404)

    def test_list_and_unsubscribe_button(self):
        search = self.subscribe_search({})
        self.webhook({"message": {"chat": {"id": CHAT_ID}, "text": "/list"}})
        self.assertIn("Toyota Camry", self.messages()[-1])
        self.webhook({"callback_query": {
            "id": "q1", "data": f"del:s:{search.pk}",
            "message": {"chat": {"id": CHAT_ID}, "message_id": 7},
        }})
        search.refresh_from_db()
        self.assertFalse(search.is_active)

    def test_stop_unsubscribes_everything(self):
        search = self.subscribe_search({})
        self.webhook({"message": {"chat": {"id": CHAT_ID}, "text": "/stop"}})
        search.refresh_from_db()
        self.assertFalse(search.is_active)


class RunAlertsTests(AlertsTestCase):
    def publish(self, dealer=None, **fields):
        return self.make_car(dealer or self.dealer_a, published_at=timezone.now(), **fields)

    def test_sends_only_new_matching_cars_once(self):
        old = self.make_car(self.dealer_a, published_at=timezone.now() - timedelta(days=1))
        search = self.subscribe_search({"model": self.model.id, "price_max": "1000000"})
        other_model = Model.objects.create(brand=self.brand, name="Test Other", slug="test-other-model")
        match = self.publish(price="900000")
        self.publish(price="2000000")  # дороже
        self.publish(model=other_model)  # другая модель
        self.publish(status=Car.Status.HIDDEN)  # скрытое — не публичное

        self.sent.clear()
        result = run_alerts()
        self.assertEqual(result["cars_sent"], 1)
        text = self.messages()[0]
        self.assertIn(f"https://autobuy.test/cars/{match.id}", text)
        self.assertIn("900 000 сом", text)
        self.assertNotIn(str(old.id), text)

        self.sent.clear()
        self.assertEqual(run_alerts()["cars_sent"], 0)
        self.assertEqual(self.messages(), [])
        self.assertEqual(search.matches.count(), 1)

    def test_search_by_text(self):
        self.subscribe_search({"search": "camry"})
        self.publish()
        self.sent.clear()
        self.assertEqual(run_alerts()["cars_sent"], 1)

    def test_price_drop_and_removed_listing(self):
        car = self.make_car(self.dealer_a, price="1000000")
        resp = self.client.post("/api/alerts/watches/", {"car": str(car.id)}, format="json")
        self.start(resp.data["bot_url"].split("?start=")[1])
        watch = PriceWatch.objects.get()

        self.sent.clear()
        run_alerts()
        self.assertEqual(self.messages(), [])  # цена не менялась

        Car.objects.filter(pk=car.pk).update(price="950000")
        run_alerts()
        self.assertIn("1 000 000 сом", self.messages()[0])
        self.assertIn("950 000 сом", self.messages()[0])
        watch.refresh_from_db()
        self.assertEqual(int(watch.last_price), 950000)

        Car.objects.filter(pk=car.pk).update(status=Car.Status.SOLD)
        run_alerts()
        self.assertIn("снято с продажи", self.messages()[-1])
        watch.refresh_from_db()
        self.assertFalse(watch.is_active)

    def test_blocked_chat_keeps_subscriptions_and_resumes(self):
        search = self.subscribe_search({})
        self.publish()

        def blocked(method, payload):
            raise telegram.BotBlocked("Forbidden: bot was blocked by the user")

        with patch("apps.alerts.telegram.call", side_effect=blocked):
            result = run_alerts()
        self.assertEqual(result["blocked"], 1)
        search.refresh_from_db()
        self.assertTrue(search.is_active)  # подписку не теряем
        self.assertTrue(TelegramChat.objects.get(chat_id=CHAT_ID).is_blocked)

        self.sent.clear()
        self.assertEqual(run_alerts()["cars_sent"], 0)  # недоступному чату не пишем
        self.webhook({"message": {"chat": {"id": CHAT_ID}, "text": "/list"}})  # человек вернулся
        self.assertFalse(TelegramChat.objects.get(chat_id=CHAT_ID).is_blocked)
        self.assertEqual(run_alerts()["cars_sent"], 1)

    def test_unclaimed_links_are_cleaned_up(self):
        self.client.post("/api/alerts/searches/", {"filters": {}}, format="json")
        SavedSearch.objects.update(created_at=timezone.now() - timedelta(days=3))
        run_alerts()
        self.assertFalse(SavedSearch.objects.exists())

    def test_cron_endpoint_sets_webhook(self):
        resp = self.client.post("/api/internal/alerts/run/", HTTP_X_CRON_SECRET="cron")
        self.assertEqual(resp.status_code, 200, resp.data)
        webhook = [p for m, p in self.sent if m == "setWebhook"][0]
        self.assertTrue(webhook["url"].endswith("/api/alerts/telegram/webhook/"))
        self.assertEqual(webhook["secret_token"], telegram.webhook_secret())
        self.assertEqual(self.client.post("/api/internal/alerts/run/", HTTP_X_CRON_SECRET="x").status_code, 403)


class WebhookAutoSetupTests(AlertsTestCase):
    def test_first_subscription_connects_bot_once(self):
        self.client.post("/api/alerts/searches/", {"filters": {}}, format="json")
        self.client.post("/api/alerts/searches/", {"filters": {}}, format="json")
        hooks = [p for m, p in self.sent if m == "setWebhook"]
        self.assertEqual(len(hooks), 1)
        self.assertTrue(hooks[0]["url"].endswith("/api/alerts/telegram/webhook/"))


@override_settings(ALERTS_RUN_INLINE=True)
class InstantNotificationTests(AlertsTestCase):
    def test_new_car_notifies_matching_search_immediately(self):
        self.subscribe_search({"model": self.model.id})
        self.sent.clear()
        with self.captureOnCommitCallbacks(execute=True):
            car = self.make_car(self.dealer_a, published_at=timezone.now())
        self.assertEqual(len(self.messages()), 1)
        self.assertIn(str(car.id), self.messages()[0])
        self.sent.clear()
        self.assertEqual(run_alerts()["cars_sent"], 0)  # повторно не присылаем

    def test_price_drop_and_sold_notify_immediately(self):
        car = self.make_car(self.dealer_a, price="1000000")
        resp = self.client.post("/api/alerts/watches/", {"car": str(car.id)}, format="json")
        self.start(resp.data["bot_url"].split("?start=")[1])
        self.sent.clear()

        car.price = "900000"
        with self.captureOnCommitCallbacks(execute=True):
            car.save()
        self.assertIn("Цена снижена", self.messages()[0])

        car.status = Car.Status.SOLD
        with self.captureOnCommitCallbacks(execute=True):
            car.save()
        self.assertIn("снято с продажи", self.messages()[-1])
        self.assertFalse(PriceWatch.objects.get().is_active)

    def test_view_counter_does_not_trigger(self):
        car = self.make_car(self.dealer_a)
        self.subscribe_search({})
        self.sent.clear()
        with self.captureOnCommitCallbacks(execute=True):
            car.save(update_fields=["views_count"])
        self.assertEqual(self.messages(), [])


@override_settings(ALERTS_RUN_INLINE=True)
class DeletedCarTests(AlertsTestCase):
    def test_deleting_car_notifies_watchers(self):
        car = self.make_car(self.dealer_a)
        resp = self.client.post("/api/alerts/watches/", {"car": str(car.id)}, format="json")
        self.start(resp.data["bot_url"].split("?start=")[1])
        self.sent.clear()
        with self.captureOnCommitCallbacks(execute=True):
            car.delete()
        self.assertEqual(len(self.messages()), 1)
        self.assertIn("снято с продажи", self.messages()[0])
        self.assertFalse(PriceWatch.objects.exists())


@override_settings(ALERTS_RUN_INLINE=True)
class NoDuplicateTests(AlertsTestCase):
    def watch_car(self, car):
        resp = self.client.post("/api/alerts/watches/", {"car": str(car.id)}, format="json")
        self.start(resp.data["bot_url"].split("?start=")[1])
        self.sent.clear()

    def test_parallel_checks_send_price_drop_once(self):
        from apps.alerts.services import notify_watch

        car = self.make_car(self.dealer_a, price="1000000")
        self.watch_car(car)
        Car.objects.filter(pk=car.pk).update(price="900000")
        # две проверки, загрузившие подписку до того, как другая её обновила
        copy1 = PriceWatch.objects.select_related("chat", "car__model__brand").get()
        copy2 = PriceWatch.objects.select_related("chat", "car__model__brand").get()
        notify_watch(copy1, {car.pk})
        notify_watch(copy2, {car.pk})
        self.assertEqual(len(self.messages()), 1)

    def test_parallel_checks_send_sold_once(self):
        from apps.alerts.services import notify_watch

        car = self.make_car(self.dealer_a)
        self.watch_car(car)
        copies = [PriceWatch.objects.select_related("chat", "car__model__brand").get() for _ in range(3)]
        for copy in copies:
            notify_watch(copy, set())
        self.assertEqual(len(self.messages()), 1)

    def test_repeated_saves_in_one_edit_send_once(self):
        car = self.make_car(self.dealer_a, price="1000000")
        self.watch_car(car)
        car.price = "950000"
        with self.captureOnCommitCallbacks(execute=True):
            car.save()
            car.save()  # кабинет сохраняет объявление несколько раз за одну правку
            car.save(update_fields=["price"])
        self.assertEqual(len(self.messages()), 1)

    def test_parallel_search_checks_send_car_once(self):
        from apps.alerts.services import notify_search
        from apps.cars.views import public_cars_queryset

        search = self.subscribe_search({})
        self.make_car(self.dealer_a, published_at=timezone.now())
        self.sent.clear()
        public = public_cars_queryset().prefetch_related(None)
        notify_search(search, public)
        notify_search(search, public)
        self.assertEqual(len(self.messages()), 1)

    def test_failed_send_releases_claim(self):
        from apps.alerts.services import notify_search
        from apps.cars.views import public_cars_queryset

        search = self.subscribe_search({})
        self.make_car(self.dealer_a, published_at=timezone.now())
        public = public_cars_queryset().prefetch_related(None)
        with patch("apps.alerts.telegram.call", return_value=None):
            self.assertEqual(notify_search(search, public), 0)
        self.assertEqual(notify_search(search, public), 1)  # повторная попытка отправит
