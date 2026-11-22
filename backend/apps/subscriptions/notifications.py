"""
Уведомления о тарифах.

Салону — письмо на email менеджеров (за 3 дня, за 1 день и в день окончания).
Администратору — сообщение в Telegram (новые заявки и ежедневная сводка).
Ошибки отправки логируются и не ломают основной запрос.
"""
import json
import logging
import math
import urllib.error
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import PlanRequest, Subscription

logger = logging.getLogger(__name__)

REMINDER_STAGES = (3, 1)  # за сколько дней напоминать
EXPIRED_LOOKBACK = timedelta(days=2)  # не писать о давно закончившихся


def frontend_url(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def send_telegram(text, token=None, chat_id=None):
    token = token or settings.TELEGRAM_BOT_TOKEN
    chat_id = chat_id or settings.TELEGRAM_ADMIN_CHAT_ID
    if not token or not chat_id:
        return False
    body = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        # Telegram объясняет причину в теле ответа, например «chat not found» —
        # бот ещё не получил /start от этого чата. Токен в лог не пишем.
        try:
            reason = json.load(exc).get("description", "")
        except Exception:
            reason = ""
        logger.error("Telegram отклонил сообщение (HTTP %s): %s", exc.code, reason or "без описания")
        return False
    except Exception as exc:
        logger.error("Не удалось отправить сообщение в Telegram: %s", type(exc).__name__)
        return False


def dealer_emails(dealer):
    return list(
        dealer.managers.filter(is_active=True, role="dealer")
        .exclude(email="")
        .values_list("email", flat=True)
    )


def send_dealer_email(dealer, subject, message):
    recipients = dealer_emails(dealer)
    if not recipients:
        return False
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
        return True
    except Exception:
        logger.exception("Не удалось отправить письмо салону %s", dealer.pk)
        return False


def notify_new_request(plan_request):
    """Новая заявка на тариф — сразу администратору в Telegram."""
    dealer = plan_request.dealer
    contact = dealer.whatsapp or dealer.phone or (plan_request.created_by.email if plan_request.created_by else "")
    price = plan_request.plan.price_for(plan_request.months)
    lines = [
        "🆕 Заявка на тариф",
        f"Салон: {dealer.name}",
        f"Тариф: {plan_request.plan.name}, {plan_request.months} мес. — {price:,.0f} сом".replace(",", " "),
    ]
    if contact:
        lines.append(f"Контакт: {contact}")
    if plan_request.comment:
        lines.append(f"Комментарий: {plan_request.comment}")
    lines.append(frontend_url("/admin/subscriptions"))
    send_telegram("\n".join(lines))


def _days_left(subscription, now):
    return max(0, math.ceil((subscription.expires_at - now).total_seconds() / 86400))


def _has_continuation(subscription):
    """Уже оплачено продление, которое начинается не позже окончания текущего."""
    return Subscription.objects.filter(
        dealer_id=subscription.dealer_id,
        starts_at__gt=subscription.starts_at,
        starts_at__lte=subscription.expires_at,
        expires_at__gt=subscription.expires_at,
    ).exists()


def _mark(subscription, stage):
    subscription.reminders_sent = [*subscription.reminders_sent, stage]
    subscription.save(update_fields=("reminders_sent",))


def send_subscription_reminders(now=None):
    """
    Запускается раз в день. Повторный запуск в тот же день ничего не дублирует:
    отправленные этапы хранятся в Subscription.reminders_sent.
    """
    now = now or timezone.now()
    link = frontend_url("/dashboard/subscription")
    expiring, expired = [], []

    for sub in Subscription.objects.current(now).select_related("dealer", "plan"):
        if not sub.dealer.is_active or _has_continuation(sub):
            continue
        days = _days_left(sub, now)
        stage = next((str(s) for s in sorted(REMINDER_STAGES) if days <= s), None)
        if stage is None or stage in sub.reminders_sent:
            continue
        what = "Пробный период" if sub.is_trial else f"Тариф «{sub.plan.name}»"
        send_dealer_email(
            sub.dealer,
            f"AutoBuy: {what.lower() if sub.is_trial else what} заканчивается через {days} дн.",
            (
                f"Здравствуйте!\n\n{what} салона «{sub.dealer.name}» заканчивается "
                f"{timezone.localtime(sub.expires_at):%d.%m.%Y} (через {days} дн.).\n"
                "После окончания объявления будут скрыты с сайта (не удалены).\n\n"
                f"Чтобы продлить, оставьте заявку в кабинете: {link}\n\nКоманда AutoBuy"
            ),
        )
        # Отмечаем все прошедшие этапы, чтобы при «3 → 1» не прийти двумя письмами в один день
        sub.reminders_sent = sorted({*sub.reminders_sent, *[str(s) for s in REMINDER_STAGES if days <= s]})
        sub.save(update_fields=("reminders_sent",))
        expiring.append((sub, days))

    recent = (
        Subscription.objects.filter(expires_at__lte=now, expires_at__gt=now - EXPIRED_LOOKBACK)
        .select_related("dealer", "plan")
        .order_by("dealer_id", "-expires_at")
    )
    seen = set()
    for sub in recent:
        if sub.dealer_id in seen:
            continue
        seen.add(sub.dealer_id)
        if (
            "expired" in sub.reminders_sent
            or not sub.dealer.is_active
            or Subscription.objects.current(now).filter(dealer_id=sub.dealer_id).exists()
        ):
            continue
        send_dealer_email(
            sub.dealer,
            "AutoBuy: тариф закончился — объявления скрыты",
            (
                f"Здравствуйте!\n\nТариф салона «{sub.dealer.name}» закончился. "
                "Объявления скрыты с сайта, но сохранены — после продления они вернутся автоматически.\n\n"
                f"Продлить: {link}\n\nКоманда AutoBuy"
            ),
        )
        _mark(sub, "expired")
        expired.append(sub)

    new_requests = PlanRequest.objects.filter(status=PlanRequest.Status.NEW).count()
    if expiring or expired or new_requests:
        lines = ["📋 Тарифы — сводка на сегодня"]
        if expiring:
            lines.append("\nЗаканчиваются:")
            lines += [f"• {s.dealer.name} — {s.plan.name}{' (пробный)' if s.is_trial else ''}, {d} дн." for s, d in expiring]
        if expired:
            lines.append("\nЗакончились (объявления скрыты):")
            lines += [f"• {s.dealer.name} — {s.plan.name}" for s in expired]
        if new_requests:
            lines.append(f"\nНеобработанных заявок: {new_requests}")
        lines.append(frontend_url("/admin/subscriptions"))
        send_telegram("\n".join(lines))

    return {"expiring": len(expiring), "expired": len(expired), "new_requests": new_requests}
