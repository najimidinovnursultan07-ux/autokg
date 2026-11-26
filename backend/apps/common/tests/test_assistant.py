from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.common.testing import MarketplaceTestCase

URL = "/api/assistant/chat/"


def text_reply(text):
    return {"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}}]}


def tool_call(**args):
    return {"candidates": [{"content": {"role": "model", "parts": [
        {"functionCall": {"name": "search_cars", "args": args}},
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
        self.assertEqual(response.data, {"reply": "Здравствуйте! Чем помочь?", "cars": []})

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

    def test_validation(self):
        for body in ({}, {"messages": []}, {"messages": [{"role": "user", "text": "  "}]},
                     {"messages": [{"role": "system", "text": "x"}]},
                     {"messages": [{"role": "user", "text": "hi"}, {"role": "model", "text": "ok"}]}):
            self.assertEqual(self.client.post(URL, body, format="json").status_code, 400, body)

    @override_settings(GEMINI_API_KEY="")
    def test_without_key_is_unavailable(self):
        self.assertEqual(self.ask().status_code, 503)
