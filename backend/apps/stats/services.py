from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import RETENTION_MONTHS, CarMonthStat, DealerMonthStat, ReportDownload


def month_of(dt=None):
    """1-е число месяца (по Бишкеку) для даты/времени."""
    local = timezone.localtime(dt) if dt is not None else timezone.localtime()
    return date(local.year, local.month, 1)


def shift_month(month, delta):
    index = month.year * 12 + month.month - 1 + delta
    return date(index // 12, index % 12 + 1, 1)


def oldest_kept_month():
    """Самый ранний месяц, который ещё хранится (текущий + 11 предыдущих)."""
    return shift_month(month_of(), -(RETENTION_MONTHS - 1))


def available_months():
    current = month_of()
    return [shift_month(current, -i) for i in range(RETENTION_MONTHS)]


def car_title(car):
    return f"{car.model.brand.name} {car.model.name}, {car.year}"


def _bump(model, lookup, defaults, **fields):
    """Атомарно увеличивает счётчики строки месяца (создаёт строку при первом событии)."""
    updates = {k: F(k) + v for k, v in fields.items()}
    if model.objects.filter(**lookup).update(**updates):
        return
    try:
        with transaction.atomic():
            model.objects.create(**lookup, **defaults, **fields)
    except IntegrityError:  # параллельный запрос успел создать строку
        model.objects.filter(**lookup).update(**updates)


def _record(car, at=None, **fields):
    month = month_of(at)
    _bump(DealerMonthStat, {"dealer_id": car.dealer_id, "month": month}, {}, **fields)
    car_fields = {k: v for k, v in fields.items() if k in ("views", "phone_views", "whatsapp_clicks")}
    if car_fields:
        _bump(
            CarMonthStat,
            {"car_id": car.pk, "month": month},
            {"dealer_id": car.dealer_id, "car_title": car_title(car)[:200]},
            **car_fields,
        )


def record_view(car):
    _record(car, views=1)


def record_contact(car, kind):
    _record(car, **{"phone_views" if kind == "phone" else "whatsapp_clicks": 1})


def record_added(car):
    _record(car, at=car.created_at, cars_added=1)


def record_sold(car):
    _record(car, at=car.sold_at, cars_sold=1)


def record_unsold(car, sold_at):
    """Продажу отменили — убираем её из месяца, в котором она была учтена."""
    if sold_at is None:
        return
    DealerMonthStat.objects.filter(
        dealer_id=car.dealer_id, month=month_of(sold_at), cars_sold__gt=0
    ).update(cars_sold=F("cars_sold") - 1)


def purge_old_stats():
    """Удаляет статистику и журнал скачиваний старше 12 месяцев."""
    oldest = oldest_kept_month()
    removed = DealerMonthStat.objects.filter(month__lt=oldest).delete()[0]
    removed += CarMonthStat.objects.filter(month__lt=oldest).delete()[0]
    removed += ReportDownload.objects.filter(report_month__lt=oldest).delete()[0]
    return removed
