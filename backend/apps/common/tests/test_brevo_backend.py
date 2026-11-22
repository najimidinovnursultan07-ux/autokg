import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

from django.core.mail import send_mail
from django.test import SimpleTestCase, override_settings


BACKEND = {
    "EMAIL_BACKEND": "apps.common.email_backends.BrevoEmailBackend",
    "BREVO_API_KEY": "test-key",
    "DEFAULT_FROM_EMAIL": "AutoBuy <no-reply@autobuy.kg>",
}


@override_settings(**BACKEND)
class BrevoBackendTests(SimpleTestCase):
    @patch("apps.common.email_backends.urllib.request.urlopen")
    def test_sends_json_to_brevo(self, urlopen):
        response = MagicMock(status=201)
        urlopen.return_value.__enter__.return_value = response

        self.assertEqual(send_mail("Тема", "Текст", None, ["dealer@test.kg"]), 1)

        request = urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.get_header("Api-key"), "test-key")
        body = json.loads(request.data)
        self.assertEqual(body["sender"], {"email": "no-reply@autobuy.kg", "name": "AutoBuy"})
        self.assertEqual(body["to"], [{"email": "dealer@test.kg"}])
        self.assertEqual(body["subject"], "Тема")
        self.assertEqual(body["textContent"], "Текст")

    @patch("apps.common.email_backends.urllib.request.urlopen")
    def test_brevo_error_is_raised_with_reason(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "url", 400, "Bad Request", {}, io.BytesIO(b'{"message": "sender not valid"}')
        )
        with self.assertRaisesMessage(RuntimeError, "sender not valid"):
            send_mail("Тема", "Текст", None, ["dealer@test.kg"])
