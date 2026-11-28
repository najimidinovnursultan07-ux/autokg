"""Минимальный клиент Bot API для бота уведомлений (TELEGRAM_ALERTS_BOT_TOKEN)."""
import hashlib
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BotBlocked(Exception):
    """Пользователь заблокировал бота или удалил чат — писать ему больше нельзя."""


def bot_token():
    return getattr(settings, "TELEGRAM_ALERTS_BOT_TOKEN", "")


def bot_username():
    configured = getattr(settings, "TELEGRAM_ALERTS_BOT_USERNAME", "").lstrip("@")
    if configured or not bot_token():
        return configured
    key = f"alerts-bot-username:{webhook_secret()[:12]}"
    username = cache.get(key)
    if not username:
        try:
            username = (call("getMe", {}) or {}).get("username", "")
        except BotBlocked:
            username = ""
        if username:
            cache.set(key, username, 60 * 60 * 24)
    return username or ""


def is_configured():
    return bool(bot_token() and bot_username())


def webhook_secret():
    """Секрет вебхука выводится из токена — отдельная переменная окружения не нужна."""
    return hashlib.sha256(f"autobuy-alerts:{bot_token()}".encode()).hexdigest()[:48]


def start_link(payload):
    return f"https://t.me/{bot_username()}?start={payload}"


def call(method, payload):
    """Вызов метода Bot API. Возвращает result или None; BotBlocked при 403."""
    token = bot_token()
    if not token:
        return None
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.load(response).get("result")
    except urllib.error.HTTPError as exc:
        try:
            reason = json.load(exc).get("description", "")
        except Exception:
            reason = ""
        if exc.code == 403 or "chat not found" in reason:
            raise BotBlocked(reason) from None
        logger.error("Telegram %s: HTTP %s %s", method, exc.code, reason or "без описания")
    except Exception as exc:
        # Токен в лог не пишем: он есть в URL запроса
        logger.error("Telegram %s: %s", method, type(exc).__name__)
    return None


def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    return call("sendMessage", payload)


def ensure_webhook(url):
    """Ставит вебхук и меню команд, если они ещё не настроены на этот адрес."""
    info = call("getWebhookInfo", {}) or {}
    if info.get("url") == url:
        return False
    call("setWebhook", {
        "url": url,
        "secret_token": webhook_secret(),
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": False,
    })
    call("setMyCommands", {"commands": [
        {"command": "list", "description": "Мои подписки"},
        {"command": "stop", "description": "Отписаться от всего"},
    ]})
    return True
