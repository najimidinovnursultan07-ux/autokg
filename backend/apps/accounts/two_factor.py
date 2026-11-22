"""
Двухфакторный вход для администраторов: после пароля бот присылает
в Telegram одноразовый 6-значный код.

Код хранится в БД только в виде HMAC (не в кэше: у gunicorn несколько
процессов, у каждого свой кэш). Код живёт 5 минут, даёт 5 попыток,
используется один раз. Новый вход отменяет прошлые неиспользованные коды.

Аварийное отключение: переменная окружения ADMIN_2FA_ENABLED=false.
"""
import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import LoginChallenge, User


logger = logging.getLogger(__name__)

CODE_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5


class TwoFactorError(Exception):
    def __init__(self, message, restart=False):
        super().__init__(message)
        self.restart = restart  # код больше не годится — нужно заново ввести пароль


def telegram_credentials():
    """Бот и чат для кодов: отдельные (TELEGRAM_BOT_ADMIN_TOKEN / TELEGRAM_ADMIN_2FA_CHAT_ID) или общие."""
    token = getattr(settings, "TELEGRAM_BOT_ADMIN_TOKEN", "") or settings.TELEGRAM_BOT_TOKEN
    chat_id = getattr(settings, "TELEGRAM_ADMIN_2FA_CHAT_ID", "") or settings.TELEGRAM_ADMIN_CHAT_ID
    return token, chat_id


def telegram_configured():
    return all(telegram_credentials())


def requires_two_factor(user):
    if not getattr(settings, "ADMIN_2FA_ENABLED", True) or user.role != User.Role.ADMIN:
        return False
    if not telegram_configured():
        logger.warning("2FA для админа пропущен: Telegram-бот не настроен (TELEGRAM_BOT_ADMIN_TOKEN или TELEGRAM_BOT_TOKEN + чат)")
        return False
    return True


def _hash(challenge_id, code):
    message = f"{challenge_id}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def start_challenge(user, ip=""):
    """Создаёт код и отправляет его в Telegram. TwoFactorError — если не отправился."""
    from apps.subscriptions.notifications import send_telegram

    now = timezone.now()
    LoginChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    LoginChallenge.objects.filter(expires_at__lt=now - timedelta(days=1)).delete()

    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge = LoginChallenge(user=user, expires_at=now + CODE_TTL)
    challenge.code_hash = _hash(challenge.id, code)
    challenge.save()

    sent = send_telegram(
        f"🔐 Код входа в админку AutoBuy: {code}\n"
        f"Действует 5 минут. Аккаунт: {user.email}"
        + (f", IP: {ip}" if ip else "")
        + "\n\nЕсли это не вы — никому не сообщайте код и срочно смените пароль.",
        *telegram_credentials(),
    )
    if not sent:
        challenge.delete()
        raise TwoFactorError("Не удалось отправить код в Telegram. Попробуйте ещё раз.")
    return challenge


def verify_challenge(challenge_id, code):
    """Возвращает пользователя при верном коде, иначе TwoFactorError."""
    code = str(code or "").strip()
    try:
        challenge = LoginChallenge.objects.select_related("user").get(pk=challenge_id)
    except (LoginChallenge.DoesNotExist, ValueError, TypeError):
        raise TwoFactorError("Код устарел. Войдите заново.", restart=True)

    now = timezone.now()
    if challenge.used_at or challenge.expires_at <= now or challenge.attempts >= MAX_ATTEMPTS:
        raise TwoFactorError("Код устарел. Войдите заново.", restart=True)

    if not (len(code) == 6 and code.isdigit() and hmac.compare_digest(challenge.code_hash, _hash(challenge.id, code))):
        challenge.attempts += 1
        if challenge.attempts >= MAX_ATTEMPTS:
            challenge.used_at = now
        challenge.save(update_fields=("attempts", "used_at"))
        left = MAX_ATTEMPTS - challenge.attempts
        if left <= 0:
            raise TwoFactorError("Слишком много неверных кодов. Войдите заново.", restart=True)
        raise TwoFactorError(f"Неверный код. Осталось попыток: {left}.")

    challenge.used_at = now
    challenge.save(update_fields=("used_at",))
    if not challenge.user.is_active:
        raise TwoFactorError("Аккаунт отключён.", restart=True)
    return challenge.user
