"""Подписки покупателей: подбор новых объявлений, снижение цен, команды бота."""
import logging
from datetime import timedelta
from html import escape
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from . import telegram
from .models import PriceWatch, SavedSearch, SearchMatch, TelegramChat

logger = logging.getLogger(__name__)

# Параметры каталога, которые можно сохранить в подписке (как в URL /catalog)
FILTER_KEYS = (
    "vehicle_type", "search", "brand", "model", "city", "dealer",
    "price_min", "price_max", "year_min", "year_max", "mileage_min", "mileage_max",
    "engine_type", "transmission", "drive_type", "body_type", "condition", "currency", "murabaha",
)
SEARCH_FIELDS = ("model__brand__name", "model__name", "city__name", "dealer__name", "description")
MAX_SUBSCRIPTIONS_PER_CHAT = 20
CARS_PER_MESSAGE = 10
UNCLAIMED_TTL = timedelta(days=2)


# ── Фильтры ────────────────────────────────────────────────────────────────

def clean_filters(raw):
    """Оставляет только известные параметры каталога с непустыми короткими значениями."""
    if not isinstance(raw, dict):
        return {}
    cleaned = {}
    for key in FILTER_KEYS:
        value = raw.get(key)
        if value is None or isinstance(value, (dict, list)):
            continue
        value = str(value).strip()[:100]
        if value:
            cleaned[key] = value
    return cleaned


def filter_cars(queryset, filters):
    from apps.cars.filters import CarFilter

    data = {k: v for k, v in filters.items() if k != "search"}
    queryset = CarFilter(data=data, queryset=queryset).qs
    for term in filters.get("search", "").split():
        condition = Q()
        for field in SEARCH_FIELDS:
            condition |= Q(**{f"{field}__icontains": term})
        queryset = queryset.filter(condition)
    return queryset


def ensure_title(title, filters):
    """Описание подписки приходит с сайта; если его нет — собираем простое из фильтров."""
    title = " ".join((title or "").split())[:200]
    if title:
        return title
    parts = []
    if filters.get("search"):
        parts.append(f"«{filters['search']}»")
    if filters.get("price_min"):
        parts.append(f"от {format_price(float(filters['price_min']), filters.get('currency'))}")
    if filters.get("price_max"):
        parts.append(f"до {format_price(float(filters['price_max']), filters.get('currency'))}")
    if filters.get("year_min"):
        parts.append(f"от {filters['year_min']} г.")
    return ", ".join(parts) or "Все новые объявления"


def filters_are_valid(filters):
    from apps.cars.filters import CarFilter
    from apps.cars.models import Car

    data = {k: v for k, v in filters.items() if k != "search"}
    return CarFilter(data=data, queryset=Car.objects.none()).is_valid()


# ── Форматирование ─────────────────────────────────────────────────────────

def site_url(path):
    return f"{settings.FRONTEND_URL.rstrip('/')}{path}"


def format_price(value, currency):
    amount = f"{int(value):,}".replace(",", " ")
    return f"${amount}" if currency == "USD" else f"{amount} сом"


def car_title(car):
    return f"{car.model.brand.name} {car.model.name} {car.year}"


def car_line(car):
    details = ", ".join(filter(None, [format_price(car.price, car.currency), car.city.name if car.city_id else ""]))
    return f'• <a href="{escape(site_url(f"/cars/{car.pk}"))}">{escape(car_title(car))}</a> — {escape(details)}'


# ── Команды бота ───────────────────────────────────────────────────────────

WELCOME = (
    "👋 Это бот уведомлений <b>AutoBuy</b>.\n\n"
    "Чтобы подписаться, откройте каталог на сайте, выберите фильтры и нажмите "
    "«Получать новые в Telegram». На странице объявления есть кнопка «Следить за ценой».\n\n"
    "/list — мои подписки\n/stop — отписаться от всего"
)


def get_chat(message):
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    obj, _ = TelegramChat.objects.update_or_create(
        chat_id=chat["id"],
        defaults={
            "username": (sender.get("username") or "")[:64],
            "first_name": (sender.get("first_name") or "")[:128],
            "is_blocked": False,
        },
    )
    return obj


def active_count(chat):
    return (
        chat.searches.filter(is_active=True).count()
        + chat.watches.filter(is_active=True).count()
    )


def claim(chat, payload):
    """Привязывает подписку из ссылки ?start=s_<токен> / w_<токен> к чату."""
    kind, _, token = payload.partition("_")
    model = {"s": SavedSearch, "w": PriceWatch}.get(kind)
    if not model or not token:
        return WELCOME
    item = model.objects.select_related("chat").filter(token=token, is_active=True).first()
    if item is None:
        return "Ссылка устарела. Вернитесь на сайт и нажмите кнопку подписки ещё раз."
    if item.chat_id and item.chat_id != chat.pk:
        return "Эта ссылка уже использована в другом чате. Нажмите кнопку подписки на сайте ещё раз."
    if item.chat_id is None:
        if active_count(chat) >= MAX_SUBSCRIPTIONS_PER_CHAT:
            return f"У вас уже {MAX_SUBSCRIPTIONS_PER_CHAT} подписок. Удалите лишние через /list."
        item.chat = chat
        if model is SavedSearch:
            item.subscribed_at = timezone.now()
            item.save(update_fields=["chat", "subscribed_at"])
        else:
            item.save(update_fields=["chat"])
    if model is SavedSearch:
        return (
            f"✅ Подписка оформлена: <b>{escape(item.title)}</b>\n\n"
            "Пришлю новые объявления, как только они появятся. Все подписки — /list"
        )
    car = item.car
    return (
        f"✅ Слежу за ценой: <b>{escape(car_title(car))}</b> — сейчас "
        f"{escape(format_price(item.last_price, item.currency))}.\n\n"
        "Напишу, если цена снизится или объявление снимут с продажи. Все подписки — /list"
    )


def list_subscriptions(chat):
    searches = list(chat.searches.filter(is_active=True))
    watches = list(chat.watches.filter(is_active=True).select_related("car__model__brand"))
    if not searches and not watches:
        return "У вас нет активных подписок.\n\n" + WELCOME, None
    lines, buttons = ["<b>Ваши подписки:</b>"], []
    for i, search in enumerate(searches, 1):
        lines.append(f"🔎 {i}. {escape(search.title)}")
        buttons.append([{"text": f"❌ Поиск {i}", "callback_data": f"del:s:{search.pk}"}])
    for i, watch in enumerate(watches, 1):
        lines.append(f"💰 {i}. {escape(car_title(watch.car))}")
        buttons.append([{"text": f"❌ Цена {i}", "callback_data": f"del:w:{watch.pk}"}])
    return "\n".join(lines), buttons


def stop_all(chat):
    chat.searches.filter(is_active=True).update(is_active=False)
    chat.watches.filter(is_active=True).update(is_active=False)
    return "Вы отписались от всех уведомлений. Подписаться снова можно на сайте."


def handle_message(message):
    text = (message.get("text") or "").strip()
    if not text.startswith("/") or "id" not in (message.get("chat") or {}):
        return
    chat = get_chat(message)
    command, _, argument = text.partition(" ")
    command = command.split("@")[0].lower()
    buttons = None
    logger.info("Бот уведомлений: чат %s, команда %s%s", chat.pk, command, " (ссылка)" if argument.strip() else "")
    if command == "/start":
        reply = claim(chat, argument.strip()) if argument.strip() else WELCOME
    elif command == "/list":
        reply, buttons = list_subscriptions(chat)
    elif command == "/stop":
        reply = stop_all(chat)
    else:
        reply = WELCOME
    telegram.send_message(chat.chat_id, reply, buttons)


def handle_callback(callback):
    data = callback.get("data") or ""
    message = callback.get("message") or {}
    chat = TelegramChat.objects.filter(chat_id=(message.get("chat") or {}).get("id")).first()
    answer = "Готово"
    parts = data.split(":")
    if chat and len(parts) == 3 and parts[0] == "del" and parts[2].isdigit():
        manager = {"s": chat.searches, "w": chat.watches}.get(parts[1])
        if manager is not None:
            manager.filter(pk=int(parts[2])).update(is_active=False)
            answer = "Подписка удалена"
        text, buttons = list_subscriptions(chat)
        telegram.call("editMessageText", {
            "chat_id": chat.chat_id,
            "message_id": message.get("message_id"),
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": buttons or []},
        })
    telegram.call("answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": answer})


def handle_update(update):
    try:
        if "message" in update:
            handle_message(update["message"])
        elif "callback_query" in update:
            handle_callback(update["callback_query"])
    except telegram.BotBlocked as exc:
        chat_id = ((update.get("message") or {}).get("chat") or {}).get("id")
        if chat_id:
            mark_blocked(TelegramChat.objects.filter(chat_id=chat_id).first(), str(exc))


def mark_blocked(chat, reason=""):
    """
    Telegram не даёт писать в чат (бот заблокирован, чат удалён). Подписки НЕ удаляем:
    рассылка пропускает такой чат, а когда человек снова напишет боту, всё продолжит работать.
    """
    if chat is None:
        return
    logger.warning("Бот уведомлений: чат %s недоступен (%s)", chat.pk, reason or "без описания")
    chat.is_blocked = True
    chat.save(update_fields=["is_blocked"])


# ── Периодическая рассылка ─────────────────────────────────────────────────

def notify_search(search, public_cars):
    since = search.subscribed_at or search.created_at
    cars = list(
        filter_cars(public_cars, search.filters)
        .filter(published_at__gt=since)
        .exclude(pk__in=SearchMatch.objects.filter(search=search).values("car_id"))
        .order_by("-published_at")
    )
    if not cars:
        return 0
    lines = [f"🔔 Новые объявления по подписке «<b>{escape(search.title)}</b>»:", ""]
    lines += [car_line(car) for car in cars[:CARS_PER_MESSAGE]]
    if len(cars) > CARS_PER_MESSAGE:
        link = site_url(f"/catalog?{urlencode(search.filters)}")
        lines += ["", f'И ещё {len(cars) - CARS_PER_MESSAGE}: <a href="{escape(link)}">смотреть все</a>']
    if telegram.send_message(search.chat.chat_id, "\n".join(lines)) is None:
        return 0  # сеть или Telegram недоступны — попробуем в следующий раз
    SearchMatch.objects.bulk_create(
        [SearchMatch(search=search, car=car) for car in cars], ignore_conflicts=True
    )
    return len(cars)


def notify_watch(watch, public_ids):
    car = watch.car
    url = escape(site_url(f"/cars/{car.pk}"))
    title = escape(car_title(car))
    if car.pk not in public_ids:
        telegram.send_message(
            watch.chat.chat_id,
            f'🚫 Объявление <a href="{url}">{title}</a> снято с продажи. Слежение остановлено.',
        )
        watch.is_active = False
        watch.save(update_fields=["is_active"])
        return 1
    if car.currency == watch.currency and car.price < watch.last_price:
        old, new = format_price(watch.last_price, watch.currency), format_price(car.price, car.currency)
        telegram.send_message(
            watch.chat.chat_id,
            f'📉 Цена снижена: <a href="{url}">{title}</a>\n<s>{escape(old)}</s> → <b>{escape(new)}</b>',
        )
        sent = 1
    else:
        sent = 0
    if car.price != watch.last_price or car.currency != watch.currency:
        watch.last_price, watch.currency = car.price, car.currency
        watch.save(update_fields=["last_price", "currency"])
    return sent


def run_alerts(now=None):
    """Вызывается по расписанию (GitHub Actions каждые 30 минут)."""
    from apps.cars.views import public_cars_queryset

    now = now or timezone.now()
    result = {"searches": 0, "cars_sent": 0, "price_messages": 0, "blocked": 0}
    if not telegram.is_configured():
        result["skipped"] = "TELEGRAM_ALERTS_BOT_TOKEN не задан"
        return result

    # Ссылки, по которым так и не нажали «Старт», не копим
    SavedSearch.objects.filter(chat__isnull=True, created_at__lt=now - UNCLAIMED_TTL).delete()
    PriceWatch.objects.filter(chat__isnull=True, created_at__lt=now - UNCLAIMED_TTL).delete()

    public_cars = public_cars_queryset().prefetch_related(None)
    searches = SavedSearch.objects.filter(is_active=True, chat__isnull=False, chat__is_blocked=False).select_related("chat")
    blocked = set()
    for search in searches:
        if search.chat_id in blocked:
            continue
        try:
            with transaction.atomic():
                result["cars_sent"] += notify_search(search, public_cars)
            result["searches"] += 1
        except telegram.BotBlocked as exc:
            mark_blocked(search.chat, str(exc))
            blocked.add(search.chat_id)
            result["blocked"] += 1

    watches = list(
        PriceWatch.objects.filter(is_active=True, chat__isnull=False, chat__is_blocked=False)
        .select_related("chat", "car__model__brand")
    )
    public_ids = set(public_cars.filter(pk__in=[w.car_id for w in watches]).values_list("pk", flat=True))
    for watch in watches:
        if watch.chat_id in blocked:
            continue
        try:
            result["price_messages"] += notify_watch(watch, public_ids)
        except telegram.BotBlocked as exc:
            mark_blocked(watch.chat, str(exc))
            blocked.add(watch.chat_id)
            result["blocked"] += 1
    return result
