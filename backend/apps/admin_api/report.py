"""
Сводный отчёт по всем автосалонам для администратора.

За выбранный период: новые объявления, полученная оплата за тарифы,
использованные продвижения, новые отзывы и заявки.
За всё время (счётчики без дат): просмотры, открытия номера, WhatsApp.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO

from django.db.models import Avg, Count, Max, Q, Sum
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.cars.models import Car, not_expired_q
from apps.dealers.models import Dealer, DealerReview
from apps.payments.models import Promotion
from apps.subscriptions.models import PlanRequest, Subscription

EXPIRING_DAYS = 7
CENTS = Decimal("0.01")


def money(value):
    return str(Decimal(value or 0).quantize(CENTS))


def parse_period(params):
    """?from=YYYY-MM-DD&to=YYYY-MM-DD (включительно). По умолчанию — текущий месяц."""
    today = timezone.localdate()
    try:
        start = date.fromisoformat(params["from"]) if params.get("from") else today.replace(day=1)
        end = date.fromisoformat(params["to"]) if params.get("to") else today
    except ValueError:
        raise ValidationError({"detail": "Даты периода — в формате ГГГГ-ММ-ДД."})
    if start > end:
        raise ValidationError({"detail": "Начало периода позже конца."})
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    return start, end, start_dt, end_dt


def _by_dealer(qs, **aggregates):
    return {row.pop("dealer"): row for row in qs.values("dealer").annotate(**aggregates).order_by()}


def build_report(start_dt, end_dt):
    now = timezone.now()
    in_period = {"created_at__gte": start_dt, "created_at__lt": end_dt}

    dealers = list(Dealer.objects.select_related("city").order_by("name"))

    current = {}
    for sub in Subscription.objects.current(now).select_related("plan").order_by("starts_at"):
        current[sub.dealer_id] = sub
    paid_until = dict(
        Subscription.objects.values("dealer").annotate(last=Max("expires_at")).values_list("dealer", "last")
    )

    active = Q(status=Car.Status.ACTIVE)
    cars = _by_dealer(
        Car.objects.all(),
        total=Count("id"),
        live=Count("id", filter=active & not_expired_q(at=now)),
        expired=Count("id", filter=active & Q(expires_at__lte=now)),
        hidden=Count("id", filter=Q(status=Car.Status.HIDDEN)),
        sold=Count("id", filter=Q(status=Car.Status.SOLD)),
        added=Count("id", filter=Q(**in_period)),
        views=Sum("views_count"),
        phone_views=Sum("phone_views"),
        whatsapp_clicks=Sum("whatsapp_clicks"),
    )

    promotions = {}
    for row in (
        Promotion.objects.filter(**in_period)
        .values("car__dealer", "promotion_type").annotate(n=Count("id")).order_by()
    ):
        promotions.setdefault(row["car__dealer"], {})[row["promotion_type"]] = row["n"]

    revenue = _by_dealer(
        Subscription.objects.filter(amount__isnull=False, **in_period),
        amount=Sum("amount"), payments=Count("id"),
    )
    published = Q(status=DealerReview.Status.PUBLISHED)
    reviews = _by_dealer(
        DealerReview.objects.all(),
        rating=Avg("rating", filter=published),
        published=Count("id", filter=published),
        pending=Count("id", filter=Q(status=DealerReview.Status.PENDING)),
        new=Count("id", filter=Q(**in_period)),
    )
    managers = _by_dealer(
        User.objects.filter(role=User.Role.DEALER, dealer__isnull=False),
        total=Count("id"), active=Count("id", filter=Q(is_active=True)),
    )
    requests = _by_dealer(PlanRequest.objects.filter(status=PlanRequest.Status.NEW), n=Count("id"))

    rows = []
    for dealer in dealers:
        sub = current.get(dealer.pk)
        c = cars.get(dealer.pk, {})
        views = c.get("views") or 0
        contacts = (c.get("phone_views") or 0) + (c.get("whatsapp_clicks") or 0)
        promo = promotions.get(dealer.pk, {})
        rev = revenue.get(dealer.pk, {})
        rv = reviews.get(dealer.pk, {})
        mg = managers.get(dealer.pk, {})
        visible = dealer.is_active and sub is not None
        days_left = max(0, -(-int((sub.expires_at - now).total_seconds()) // 86400)) if sub else None
        rows.append({
            "dealer": dealer.pk,
            "name": dealer.name,
            "slug": dealer.slug,
            "city": dealer.city.name if dealer.city else "",
            "phone": dealer.phone or dealer.whatsapp,
            "is_active": dealer.is_active,
            "plan": sub.plan.name if sub else None,
            "plan_code": sub.plan.code if sub else None,
            "is_trial": bool(sub and sub.is_trial),
            "expires_at": sub.expires_at if sub else None,
            "days_left": days_left,
            "paid_until": paid_until.get(dealer.pk),
            "max_cars": sub.plan.max_active_cars if sub else 0,
            "cars_total": c.get("total", 0),
            "cars_live": c.get("live", 0),
            "cars_on_site": c.get("live", 0) if visible else 0,
            "cars_expired": c.get("expired", 0),
            "cars_hidden": c.get("hidden", 0),
            "cars_sold": c.get("sold", 0),
            "cars_added": c.get("added", 0),
            "views": views,
            "phone_views": c.get("phone_views") or 0,
            "whatsapp_clicks": c.get("whatsapp_clicks") or 0,
            "contact_rate": round(contacts / views * 100, 1) if views else None,
            "promo_top": promo.get("top", 0),
            "promo_highlight": promo.get("highlight", 0),
            "promo_urgent": promo.get("urgent", 0),
            "revenue": money(rev.get("amount")),
            "payments": rev.get("payments", 0),
            "rating": round(float(rv["rating"]), 1) if rv.get("rating") is not None else None,
            "reviews": rv.get("published", 0),
            "reviews_pending": rv.get("pending", 0),
            "reviews_new": rv.get("new", 0),
            "managers": mg.get("active", 0),
            "new_requests": requests.get(dealer.pk, {}).get("n", 0),
        })

    def total(key):
        return sum(r[key] for r in rows)

    plans = {}
    for r in rows:
        label = "Без тарифа" if r["plan"] is None else (f"{r['plan']} (пробный)" if r["is_trial"] else r["plan"])
        plans[label] = plans.get(label, 0) + 1

    summary = {
        "dealers": len(rows),
        "dealers_active": sum(1 for r in rows if r["is_active"]),
        "dealers_paid": sum(1 for r in rows if r["plan"] and not r["is_trial"]),
        "dealers_trial": sum(1 for r in rows if r["is_trial"]),
        "dealers_without_plan": sum(1 for r in rows if r["plan"] is None),
        "expiring_soon": sum(1 for r in rows if r["days_left"] is not None and r["days_left"] <= EXPIRING_DAYS),
        "revenue": money(sum((Decimal(r["revenue"]) for r in rows), Decimal("0"))),
        "payments": total("payments"),
        "cars_total": total("cars_total"),
        "cars_on_site": total("cars_on_site"),
        "cars_expired": total("cars_expired"),
        "cars_hidden": total("cars_hidden"),
        "cars_sold": total("cars_sold"),
        "cars_added": total("cars_added"),
        "views": total("views"),
        "phone_views": total("phone_views"),
        "whatsapp_clicks": total("whatsapp_clicks"),
        "promotions": total("promo_top") + total("promo_highlight") + total("promo_urgent"),
        "reviews_new": total("reviews_new"),
        "reviews_pending": total("reviews_pending"),
        "new_requests": total("new_requests"),
    }
    return {"summary": summary, "plans": plans, "rows": rows}


# ── Excel ──────────────────────────────────────────────────────────────────

EXPORT_COLUMNS = [
    ("name", "Салон", 28), ("city", "Город", 14), ("phone", "Телефон", 16),
    ("is_active", "Салон активен", 10), ("plan", "Тариф", 14), ("is_trial", "Пробный", 9),
    ("expires_at", "Тариф до", 12), ("days_left", "Осталось дн.", 10), ("paid_until", "Оплачено до", 12),
    ("max_cars", "Лимит", 8), ("cars_on_site", "На сайте", 9), ("cars_expired", "Срок истёк", 9),
    ("cars_hidden", "Скрыто", 8), ("cars_sold", "Продано", 8), ("cars_total", "Всего авто", 9),
    ("cars_added", "Добавлено за период", 11), ("views", "Просмотры (всё время)", 12),
    ("phone_views", "Открыли номер (всё время)", 12), ("whatsapp_clicks", "WhatsApp (всё время)", 12),
    ("contact_rate", "Контакты / просмотры, %", 11), ("promo_top", "ТОП за период", 9),
    ("promo_highlight", "Выделения за период", 10), ("promo_urgent", "«Срочно» за период", 10),
    ("revenue", "Оплачено за период, сом", 14), ("payments", "Оплат", 7),
    ("rating", "Рейтинг", 8), ("reviews", "Отзывов", 8), ("reviews_new", "Новых отзывов", 9),
    ("reviews_pending", "Отзывы на проверке", 10), ("managers", "Менеджеров", 9),
    ("new_requests", "Новые заявки", 9),
]

SUMMARY_LABELS = [
    ("dealers", "Автосалонов всего"), ("dealers_active", "Активных салонов"),
    ("dealers_paid", "На платном тарифе"), ("dealers_trial", "На пробном периоде"),
    ("dealers_without_plan", "Без тарифа"), ("expiring_soon", f"Тариф заканчивается в течение {EXPIRING_DAYS} дн."),
    ("revenue", "Оплачено за период, сом"), ("payments", "Оплат за период"),
    ("cars_on_site", "Объявлений на сайте"), ("cars_expired", "Срок размещения истёк"),
    ("cars_hidden", "Скрытых"), ("cars_sold", "Проданных"), ("cars_total", "Объявлений всего"),
    ("cars_added", "Добавлено за период"), ("views", "Просмотров (всё время)"),
    ("phone_views", "Открыли номер (всё время)"), ("whatsapp_clicks", "WhatsApp (всё время)"),
    ("promotions", "Продвижений за период"), ("reviews_new", "Новых отзывов за период"),
    ("reviews_pending", "Отзывов на проверке"), ("new_requests", "Необработанных заявок на тариф"),
]


def _cell(value):
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, datetime):
        return timezone.localtime(value).date()
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            return float(Decimal(value)) if value.replace(".", "", 1).isdigit() else value
        except Exception:
            return value
    return value


def build_report_xlsx(report, start, end):
    wb = Workbook()
    bold = Font(bold=True)
    fill = PatternFill("solid", fgColor="E8F1FD")

    ws = wb.active
    ws.title = "Сводка"
    ws.append([f"Отчёт AutoBuy по автосалонам за {start:%d.%m.%Y} — {end:%d.%m.%Y}"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Сформирован {timezone.localtime():%d.%m.%Y %H:%M}"])
    ws.append([])
    for key, label in SUMMARY_LABELS:
        ws.append([label, _cell(report["summary"][key])])
    ws.append([])
    ws.append(["Тарифы", "Салонов"])
    ws.cell(row=ws.max_row, column=1).font = bold
    for label, count in report["plans"].items():
        ws.append([label, count])
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 16

    sheet = wb.create_sheet("Салоны")
    for col, (_, title, width) in enumerate(EXPORT_COLUMNS, start=1):
        cell = sheet.cell(row=1, column=col, value=title)
        cell.font = bold
        cell.fill = fill
        sheet.column_dimensions[get_column_letter(col)].width = width
    for row in report["rows"]:
        values = dict(row)
        if values["plan"] is None:
            values["plan"] = "нет"
        sheet.append([_cell(values[key]) for key, _, _ in EXPORT_COLUMNS])
    for row_cells in sheet.iter_rows(min_row=2):
        for cell in row_cells:
            if isinstance(cell.value, date):
                cell.number_format = "DD.MM.YYYY"
    sheet.freeze_panes = "B2"
    sheet.auto_filter.ref = sheet.dimensions

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
