"""
ИИ-помощник сайта на Gemini.

Ключ хранится только на сервере (GEMINI_API_KEY). Помощник отвечает на вопросы
о сайте и мурабахе и ищет автомобили в каталоге через функцию search_cars —
поэтому предлагает только реальные объявления, а не выдумывает их.
"""
import json
import logging
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db.models import Q

logger = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TOOL_ROUNDS = 3
MAX_RESULTS = 6
SITE_URL_PATH = "/cars/{id}"
SUPPORT_PHONE = "+996 708 887 776"  # как во frontend/src/utils/contacts.js


class AssistantUnavailable(Exception):
    """Помощник не настроен или Gemini не ответил."""


class ModelBusy(AssistantUnavailable):
    """Модель перегружена (429/5xx) — можно попробовать запасную."""


RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


SYSTEM_PROMPT = """Ты — ИИ-помощник сайта AutoBuy, площадки продажи автомобилей от проверенных автосалонов Кыргызстана.

Как отвечать:
- Отвечай на языке пользователя: по-русски или по-кыргызски. Коротко и по делу (2–5 предложений).
- Пиши обычным текстом: без markdown, звёздочек, решёток и таблиц. Для списка — строки, начинающиеся с «• ».
- Помогай подобрать автомобиль. Когда пользователь ищет машину, ВСЕГДА вызывай search_cars и предлагай только найденные объявления. Никогда не выдумывай автомобили, цены и салоны.
- Если ничего не нашлось — скажи об этом и предложи смягчить условия (бюджет, год, марку).
- Найденные автомобили покажутся пользователю карточками под твоим ответом, поэтому не перечисляй ссылки — достаточно кратко сказать, что подходит и почему.
- Цены бывают в сомах и долларах. Бюджет пользователя передавай в search_cars в той валюте, которую он назвал.

Что ты знаешь о сайте:
- Каталог: /catalog (фильтры по марке, цене, году, пробегу, кузову, мурабахе). Салоны: /dealers. Сравнение авто: /compare.
- Номер продавца открывается кнопкой «Показать номер» на странице автомобиля, там же кнопка WhatsApp салона.
- Мурабаха — исламская рассрочка без процентов: салон продаёт авто с фиксированной наценкой, известной заранее, покупатель платит первый взнос и равные ежемесячные платежи. Не все салоны и не все авто её предлагают — ищи с murabaha=true. На странице такого авто есть калькулятор платежа. Точные условия покупатель уточняет у салона.
- Совет безопасности: не переводить предоплату до личного осмотра автомобиля.
- Автосалонам: размещение по тарифам, страница /pricing. Поддержка AutoBuy в WhatsApp: {support_phone}.

Не давай юридических и финансовых гарантий. На вопросы не про автомобили и AutoBuy вежливо отвечай, что помогаешь только с покупкой авто на сайте."""

SEARCH_TOOL = {
    "name": "search_cars",
    "description": "Ищет автомобили в каталоге AutoBuy (только активные объявления). Все параметры необязательны.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Марка и/или модель, например 'Toyota Camry'"},
            "body_type": {"type": "string", "enum": ["sedan", "hatchback", "suv", "wagon", "coupe", "minivan", "pickup"]},
            "condition": {"type": "string", "enum": ["new", "used"]},
            "transmission": {"type": "string", "enum": ["manual", "automatic", "cvt", "robotic"]},
            "engine_type": {"type": "string", "enum": ["petrol", "diesel", "hybrid", "electric", "lpg"]},
            "drive_type": {"type": "string", "enum": ["fwd", "rwd", "awd"]},
            "price_min": {"type": "number"},
            "price_max": {"type": "number"},
            "currency": {"type": "string", "enum": ["KGS", "USD"], "description": "Валюта бюджета, по умолчанию KGS"},
            "year_min": {"type": "integer"},
            "year_max": {"type": "integer"},
            "mileage_max": {"type": "integer"},
            "city": {"type": "string", "description": "Город, например 'Бишкек'"},
            "murabaha": {"type": "boolean", "description": "true — только авто, доступные по мурабахе"},
            "sort": {"type": "string", "enum": ["cheapest", "newest", "lowest_mileage"]},
        },
    },
}

SORTS = {"cheapest": "price", "newest": "-year", "lowest_mileage": "mileage"}


def _usd_rate():
    from .rates import get_rates

    try:
        data = get_rates()
        return Decimal(str(data["rates"]["USD"])) if data else None
    except Exception:  # курс не критичен для поиска
        return None


def _price_q(lookup, amount, currency, usd):
    """Цена в бюджете с учётом валюты объявления (пересчёт по курсу НБКР)."""
    amount = Decimal(str(amount))
    same = Q(currency=currency, **{f"price__{lookup}": amount})
    if not usd:
        return same
    other_currency = "KGS" if currency == "USD" else "USD"
    converted = amount * usd if currency == "USD" else amount / usd
    return same | Q(currency=other_currency, **{f"price__{lookup}": converted})


def search_cars(args):
    from apps.cars.views import public_cars_queryset

    qs = public_cars_queryset()
    query = (args.get("query") or "").strip()
    for word in query.split()[:4]:
        qs = qs.filter(Q(model__brand__name__icontains=word) | Q(model__name__icontains=word))
    for field in ("body_type", "condition", "transmission", "engine_type", "drive_type"):
        if args.get(field):
            qs = qs.filter(**{field: args[field]})
    if args.get("city"):
        qs = qs.filter(city__name__icontains=str(args["city"]).strip())
    if args.get("year_min"):
        qs = qs.filter(year__gte=int(args["year_min"]))
    if args.get("year_max"):
        qs = qs.filter(year__lte=int(args["year_max"]))
    if args.get("mileage_max") is not None:
        qs = qs.filter(mileage__lte=int(args["mileage_max"]))
    if args.get("murabaha"):
        qs = qs.filter(murabaha_available=True, dealer__murabaha_enabled=True)

    currency = args.get("currency") if args.get("currency") in ("KGS", "USD") else "KGS"
    if args.get("price_min") is not None or args.get("price_max") is not None:
        usd = _usd_rate()
        if args.get("price_min") is not None:
            qs = qs.filter(_price_q("gte", args["price_min"], currency, usd))
        if args.get("price_max") is not None:
            qs = qs.filter(_price_q("lte", args["price_max"], currency, usd))

    qs = qs.order_by(SORTS.get(args.get("sort"), "-published_at"), "-created_at")
    total = qs.count()
    return total, list(qs[:MAX_RESULTS])


def car_summary(car):
    """Короткое описание авто для модели и для карточки в чате."""
    cover = next((img for img in car.images.all() if img.is_cover), None) or next(iter(car.images.all()), None)
    return {
        "id": str(car.pk),
        "title": f"{car.model.brand.name} {car.model.name} {car.year}",
        "price": float(car.price),
        "currency": car.currency,
        "mileage": car.mileage,
        "city": car.city.name if car.city_id else "",
        "dealer": car.dealer.name if car.dealer_id else "",
        "body_type": car.body_type,
        "transmission": car.transmission,
        "engine_type": car.engine_type,
        "murabaha": bool(car.murabaha_available and car.dealer and car.dealer.murabaha_enabled),
        "url": SITE_URL_PATH.format(id=car.pk),
        "image": cover,
    }


def _call_gemini(contents, model):
    key = getattr(settings, "GEMINI_API_KEY", "")
    if not key:
        raise AssistantUnavailable("GEMINI_API_KEY не задан")
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT.replace("{support_phone}", SUPPORT_PHONE)}]},
        "contents": contents,
        "tools": [{"functionDeclarations": [SEARCH_TOOL]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024},
    }
    request = Request(
        API_URL.format(model=model),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=40) as response:
            return json.load(response)
    except HTTPError as exc:
        logger.warning("Gemini %s HTTP %s: %s", model, exc.code, exc.read()[:500])
        if exc.code in RETRYABLE_STATUSES:
            raise ModelBusy("Модель перегружена") from exc
        raise AssistantUnavailable("Gemini вернул ошибку") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        logger.warning("Gemini недоступен: %s", exc)
        raise AssistantUnavailable("Gemini недоступен") from exc


def chat(history):
    """
    history — [{"role": "user"|"model", "text": "..."}], последнее сообщение от пользователя.
    Возвращает (текст ответа, найденные машины — список моделей Car).
    """
    contents = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in history]
    models = [settings.GEMINI_MODEL] + [m for m in settings.GEMINI_FALLBACK_MODELS if m != settings.GEMINI_MODEL]
    last_error = None
    for model in models:
        try:
            return _chat_with_model(contents, model)
        except ModelBusy as exc:
            last_error = exc
    raise last_error


def _chat_with_model(contents, model):
    # Весь диалог с вызовами функций — на одной модели: подписи «мыслей»
    # (thoughtSignature) одной модели другая не принимает.
    contents = list(contents)
    found = {}

    for _ in range(MAX_TOOL_ROUNDS + 1):
        data = _call_gemini(contents, model)
        candidate = (data.get("candidates") or [{}])[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            return text, list(found.values())

        contents.append({"role": "model", "parts": parts})
        responses = []
        for call in calls:
            if call.get("name") != "search_cars":
                result = {"error": "unknown function"}
            else:
                total, cars = search_cars(call.get("args") or {})
                summaries = []
                for car in cars:
                    found[car.pk] = car
                    summary = car_summary(car)
                    summary.pop("image")
                    summaries.append(summary)
                result = {"total_found": total, "cars": summaries}
            response = {"name": call.get("name"), "response": result}
            if call.get("id"):
                response["id"] = call["id"]
            responses.append({"functionResponse": response})
        contents.append({"role": "user", "parts": responses})

    return "", list(found.values())
