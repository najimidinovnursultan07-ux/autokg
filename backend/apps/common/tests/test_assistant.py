from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.common.testing import MarketplaceTestCase

URL = "/api/assistant/chat/"


def text_reply(text):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}}]}


def tool_call(name="search_cars", **args):
    return {"candidates": [{"content": {"role": "model", "parts": [
        {"functionCall": {"name": name, "args": args}},
    ]}}]}


@override_settings(GEMINI_API_KEY="test-key")
class AssistantTests(MarketplaceTestCase):
    client_class = APIClient

    def setUp(self):
        super().setUp()
        cache.clear()

    def ask(self, text="Привет"):
        return self.client.post(URL, {"messages": [{"role": "user", "text": text}]}, format="json")

    @mock.patch("apps.common.assistant._call_gemini")
    def test_plain_answer(self, gemini):
        gemini.return_value = text_reply("Здравствуйте! Чем помочь?")
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"reply": "Здравствуйте! Чем помочь?", "cars": [], "ads": [], "dealers": []})

    @mock.patch("apps.common.assistant._call_gemini")
    def test_search_returns_only_real_public_cars(self, gemini):
        cheap = self.make_car(self.dealer_a, price="500000.00")
        self.make_car(self.dealer_a, price="3000000.00")
        self.make_car(self.dealer_a, price="400000.00", status="hidden")
        gemini.side_effect = [tool_call(price_max=1000000), text_reply("Нашёл один вариант.")]

        response = self.ask("Машина до миллиона")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Нашёл один вариант.")
        self.assertEqual([car["id"] for car in response.data["cars"]], [str(cheap.pk)])
        self.assertEqual(response.data["cars"][0]["url"], f"/cars/{cheap.pk}")

        # модель получила результат поиска
        second_call_contents = gemini.call_args_list[1].args[0]
        result = second_call_contents[-1]["parts"][0]["functionResponse"]["response"]
        self.assertEqual(result["total_found"], 1)

    @mock.patch("apps.common.assistant._call_gemini")
    def test_murabaha_search(self, gemini):
        self.dealer_a.murabaha_enabled = True
        self.dealer_a.save()
        marked = self.make_car(self.dealer_a, murabaha_available=True)
        self.make_car(self.dealer_a)
        gemini.side_effect = [tool_call(murabaha=True), text_reply("Вот авто по мурабахе.")]
        response = self.ask("Что есть по мурабахе?")
        self.assertEqual([car["id"] for car in response.data["cars"]], [str(marked.pk)])
        self.assertTrue(response.data["cars"][0]["murabaha"])

    @mock.patch("apps.common.assistant._call_gemini")
    def test_falls_back_when_model_busy(self, gemini):
        from apps.common.assistant import ModelBusy

        gemini.side_effect = [ModelBusy("busy"), text_reply("Ответ запасной модели")]
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Ответ запасной модели")
        self.assertNotEqual(gemini.call_args_list[0].args[1], gemini.call_args_list[1].args[1])

    @mock.patch("apps.common.assistant._call_gemini")
    def test_shows_live_ads(self, gemini):
        import datetime

        from django.utils import timezone

        from apps.ads.models import AdBanner
        from apps.common.testing import make_image

        def banner(**extra):
            return AdBanner.objects.create(
                title="Автокредит", advertiser="Банк", placement="home_top",
                image=make_image("ad.png", fmt="PNG"),
                link_url="https://bank.example.kg", **extra,
            )

        live = banner()
        banner(is_active=False)
        banner(ends_on=timezone.localdate() - datetime.timedelta(days=1))
        gemini.side_effect = [tool_call("list_site_ads"), text_reply("Сейчас на сайте реклама банка.")]

        response = self.ask("рекламаларды бер")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([ad["id"] for ad in response.data["ads"]], [live.pk])
        self.assertNotIn("link_url", response.data["ads"][0])  # переход только через /ads/<id>/click/

    @mock.patch("apps.common.assistant._call_gemini")
    def test_dealer_search_by_name_cyrillic_and_latin(self, gemini):
        self.dealer_a.name = "Магнат"
        self.dealer_a.slug = "magnat"
        self.dealer_a.save()
        for query in ("Магнат", "Magnat"):
            gemini.side_effect = [tool_call("search_dealers", query=query), text_reply("Да, есть.")]
            response = self.ask(f"{query} автосалон барбы?")
            self.assertEqual(response.status_code, 200)
            self.assertEqual([d["slug"] for d in response.data["dealers"]], ["magnat"], query)
            sent = gemini.call_args_list[-1].args[0][-1]["parts"][0]["functionResponse"]["response"]
            self.assertEqual(sent["dealers"][0]["url"], "/dealers/magnat")

    @mock.patch("apps.common.assistant._call_gemini")
    def test_cars_of_dealer(self, gemini):
        own = self.make_car(self.dealer_a)
        self.make_car(self.dealer_b)
        gemini.side_effect = [tool_call(dealer=self.dealer_a.name), text_reply("Вот машины салона.")]
        response = self.ask("Какие машины у салона?")
        self.assertEqual([car["id"] for car in response.data["cars"]], [str(own.pk)])

    def test_kyrgyz_detection(self):
        from apps.common.assistant import looks_kyrgyz

        for text in ("рекламаларды бер", "камри барбы", "Мурабаха деген эмне?", "Унаа керек", "Сүрөт"):
            self.assertTrue(looks_kyrgyz(text), text)
        for text in ("Покажи рекламу", "Ищу Toyota Camry до 25000", "Какие авто по мурабахе?", "Привет"):
            self.assertFalse(looks_kyrgyz(text), text)

    @mock.patch("apps.common.assistant._call_gemini")
    def test_kyrgyz_question_gets_kyrgyz_rule(self, gemini):
        gemini.return_value = text_reply("Саламатсызбы!")
        self.ask("рекламаларды бер")
        self.assertIn("кыргызском", gemini.call_args.args[2])
        self.ask("Покажи рекламу")
        self.assertEqual(gemini.call_args.args[2], "")

    def test_validation(self):
        for body in ({}, {"messages": []}, {"messages": [{"role": "user", "text": "  "}]},
                     {"messages": [{"role": "system", "text": "x"}]},
                     {"messages": [{"role": "user", "text": "hi"}, {"role": "model", "text": "ok"}]}):
            self.assertEqual(self.client.post(URL, body, format="json").status_code, 400, body)

    @override_settings(GEMINI_API_KEY="")
    def test_without_key_is_unavailable(self):
        self.assertEqual(self.ask().status_code, 503)
