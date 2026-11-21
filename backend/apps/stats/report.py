"""Отчёт салона за месяц (раздел «Отчёт» в кабинете и PDF)."""
from datetime import date, datetime, time

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.cars.models import Car, not_expired_q
from apps.payments.models import Promotion
from apps.subscriptions.services import current_subscription

from .models import PDF_DOWNLOADS_PER_MONTH, RETENTION_MONTHS, CarMonthStat, DealerMonthStat, ReportDownload
from .services import available_months, car_title, month_of, purge_old_stats, shift_month

MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
COUNTERS = ("cars_added", "cars_sold", "views", "phone_views", "whatsapp_clicks")
TOP_CARS_LIMIT = 50


def month_label(month):
    return f"{MONTH_NAMES[month.month - 1]} {month.year}"


def parse_month(value):
    """'ГГГГ-ММ' → date(ГГГГ, ММ, 1). Только последние 12 месяцев."""
    if not value:
        return month_of()
    try:
        year, month = (int(part) for part in value.split("-"))
        result = date(year, month, 1)
    except (ValueError, TypeError):
        raise ValidationError({"detail": "Месяц — в формате ГГГГ-ММ."})
    if result not in available_months():
        raise ValidationError({"detail": f"Отчёт доступен только за последние {RETENTION_MONTHS} месяцев."})
    return result


def _bounds(month):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(month, time.min), tz)
    end = timezone.make_aware(datetime.combine(shift_month(month, 1), time.min), tz)
    return start, end


def _counters(dealer, month):
    row = DealerMonthStat.objects.filter(dealer=dealer, month=month).values(*COUNTERS).first()
    return row or dict.fromkeys(COUNTERS, 0)


def downloads_left(dealer):
    used = ReportDownload.objects.filter(dealer=dealer, created_at__gte=_bounds(month_of())[0]).count()
    return max(PDF_DOWNLOADS_PER_MONTH - used, 0), used


def build_dealer_report(dealer, month):
    purge_old_stats()
    now = timezone.now()
    start, end = _bounds(month)
    subscription = current_subscription(dealer)
    show_contacts = bool(subscription and subscription.plan.stats_level != "basic")

    current = _counters(dealer, month)
    previous = _counters(dealer, shift_month(month, -1))
    for counters in (current, previous):
        contacts = counters["phone_views"] + counters["whatsapp_clicks"]
        counters["contact_rate"] = round(contacts / counters["views"] * 100, 1) if counters["views"] else None
        if not show_contacts:
            counters.update(phone_views=None, whatsapp_clicks=None, contact_rate=None)

    active = Q(status=Car.Status.ACTIVE)
    listings = Car.objects.filter(dealer=dealer).aggregate(
        total=Count("id"),
        live=Count("id", filter=active & not_expired_q(at=now)),
        expired=Count("id", filter=active & Q(expires_at__lte=now)),
        hidden=Count("id", filter=Q(status=Car.Status.HIDDEN)),
        sold=Count("id", filter=Q(status=Car.Status.SOLD)),
    )
    listings["on_site"] = listings["live"] if dealer.is_active and subscription else 0
    listings["limit"] = subscription.plan.max_active_cars if subscription else 0

    top_cars = []
    for stat in (
        CarMonthStat.objects.filter(dealer=dealer, month=month)
        .select_related("car").order_by("-views", "car_title")[:TOP_CARS_LIMIT]
    ):
        car = stat.car
        top_cars.append({
            "car_id": str(car.pk) if car else None,
            "title": stat.car_title,
            "status": car.status if car else "deleted",
            "price": str(car.price) if car else None,
            "currency": car.currency if car else None,
            "views": stat.views,
            "phone_views": stat.phone_views if show_contacts else None,
            "whatsapp_clicks": stat.whatsapp_clicks if show_contacts else None,
        })

    sold = []
    for car in (
        Car.objects.filter(dealer=dealer, sold_at__gte=start, sold_at__lt=end)
        .select_related("model", "model__brand").order_by("sold_at")
    ):
        listed = car.published_at or car.created_at
        sold.append({
            "car_id": str(car.pk),
            "title": car_title(car),
            "price": str(car.price),
            "currency": car.currency,
            "sold_at": car.sold_at,
            "days_on_site": max((car.sold_at - listed).days, 0),
        })

    promotions = dict.fromkeys(("top", "highlight", "urgent"), 0)
    for row in (
        Promotion.objects.filter(car__dealer=dealer, created_at__gte=start, created_at__lt=end)
        .values("promotion_type").annotate(n=Count("id")).order_by()
    ):
        promotions[row["promotion_type"]] = row["n"]

    left, used = downloads_left(dealer)
    return {
        "dealer": {"name": dealer.name, "slug": dealer.slug},
        "month": month.strftime("%Y-%m"),
        "month_label": month_label(month),
        "is_current_month": month == month_of(),
        "months": [{"value": m.strftime("%Y-%m"), "label": month_label(m)} for m in available_months()],
        "plan": {
            "name": subscription.plan.name if subscription else None,
            "is_trial": bool(subscription and subscription.is_trial),
            "expires_at": subscription.expires_at if subscription else None,
        },
        "show_contacts": show_contacts,
        "current": current,
        "previous": previous,
        "listings": listings,
        "promotions": promotions,
        "top_cars": top_cars,
        "sold": sold,
        "downloads": {"limit": PDF_DOWNLOADS_PER_MONTH, "used": used, "left": left},
        "retention_months": RETENTION_MONTHS,
        "deleted_after": shift_month(month, RETENTION_MONTHS),
    }
