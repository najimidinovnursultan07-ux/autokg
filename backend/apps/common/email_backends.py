"""
Отправка писем через HTTP API Brevo (https://developers.brevo.com/reference/sendtransacemail).

Render блокирует исходящий SMTP (порты 465/587) на бесплатных сервисах,
а HTTPS (443) работает везде — поэтому письма идут через API, а не SMTP.
Включается переменной BREVO_API_KEY. Адрес отправителя (DEFAULT_FROM_EMAIL)
должен быть подтверждён в Brevo: Senders, Domains & Dedicated IPs → Senders.
"""
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Brevo: письмо не отправлено")
        return sent

    def _send(self, message):
        name, address = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        sender = {"email": address}
        if name:
            sender["name"] = name
        payload = {
            "sender": sender,
            "to": [{"email": parseaddr(r)[1]} for r in message.to],
            "subject": message.subject,
            "textContent": message.body,
        }
        if message.cc:
            payload["cc"] = [{"email": parseaddr(r)[1]} for r in message.cc]
        if message.bcc:
            payload["bcc"] = [{"email": parseaddr(r)[1]} for r in message.bcc]
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = content

        request = urllib.request.Request(
            BREVO_URL,
            data=json.dumps(payload).encode(),
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Brevo HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            try:
                reason = json.load(exc).get("message", "")
            except Exception:
                reason = ""
            raise RuntimeError(f"Brevo HTTP {exc.code}: {reason or 'без описания'}") from None
