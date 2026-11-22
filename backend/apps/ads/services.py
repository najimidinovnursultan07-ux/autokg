from datetime import date, timedelta
from io import BytesIO

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from rest_framework.exceptions import ValidationError

from .models import AdBanner, AdDailyStat

MAX_PERIOD_DAYS = 366


def _bump(banner_ids, field):
    """Атомарно +1 к счётчику field у баннеров и в их статистике за сегодня."""
    banner_ids = list(banner_ids)
    if not banner_ids:
        return
    today = timezone.localdate()
    with transaction.atomic():
        AdBanner.objects.filter(pk__in=banner_ids).update(**{field: F(field) + 1})
        AdDailyStat.objects.bulk_create(
            [AdDailyStat(banner_id=pk, date=today) for pk in banner_ids], ignore_conflicts=True
        )
        AdDailyStat.objects.filter(banner_id__in=banner_ids, date=today).update(**{field: F(field) + 1})


def record_impressions(banner_ids):
    _bump(banner_ids, "impressions")


def record_click(banner_id):
    _bump([banner_id], "clicks")


def ctr(impressions, clicks):
    return round(clicks * 100 / impressions, 2) if impressions else 0.0


def parse_stats_period(params, banner):
    """?from=&to= (ГГГГ-ММ-ДД). По умолчанию — с начала показа (или 30 дней назад) по сегодня."""
    today = timezone.localdate()
    default_start = banner.starts_on or timezone.localdate(banner.created_at)
    default_start = min(max(default_start, today - timedelta(days=MAX_PERIOD_DAYS - 1)), today)
    try:
        start = date.fromisoformat(params["from"]) if params.get("from") else default_start
        end = date.fromisoformat(params["to"]) if params.get("to") else today
    except ValueError:
        raise ValidationError({"detail": "Даты периода — в формате ГГГГ-ММ-ДД."})
    if end < start:
        raise ValidationError({"detail": "Дата окончания раньше даты начала."})
    if (end - start).days >= MAX_PERIOD_DAYS:
        raise ValidationError({"detail": "Период не больше года."})
    return start, end


def banner_stats(banner, start, end):
    days = list(
        banner.daily_stats.filter(date__gte=start, date__lte=end)
        .order_by("date")
        .values("date", "impressions", "clicks")
    )
    impressions = sum(row["impressions"] for row in days)
    clicks = sum(row["clicks"] for row in days)
    for row in days:
        row["ctr"] = ctr(row["impressions"], row["clicks"])
    return {
        "period": {"from": start, "to": end},
        "totals": {"impressions": impressions, "clicks": clicks, "ctr": ctr(impressions, clicks)},
        "days": days,
    }


def banner_stats_xlsx(banner, stats):
    start, end = stats["period"]["from"], stats["period"]["to"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Статистика"
    bold = Font(bold=True)
    ws.append([f"Отчёт по рекламе на AutoBuy: {banner.advertiser}"])
    ws["A1"].font = Font(bold=True, size=13)
    ws.append([f"Баннер: {banner.title} ({banner.get_placement_display()})"])
    ws.append([f"Период: {start:%d.%m.%Y} — {end:%d.%m.%Y}"])
    ws.append([])
    ws.append(["Показы", stats["totals"]["impressions"]])
    ws.append(["Клики", stats["totals"]["clicks"]])
    ws.append(["CTR, %", stats["totals"]["ctr"]])
    ws.append([])
    ws.append(["День", "Показы", "Клики", "CTR, %"])
    fill = PatternFill("solid", fgColor="E8F1FD")
    for cell in ws[ws.max_row]:
        cell.font = bold
        cell.fill = fill
    for row in stats["days"]:
        ws.append([row["date"], row["impressions"], row["clicks"], row["ctr"]])
        ws.cell(row=ws.max_row, column=1).number_format = "DD.MM.YYYY"
    ws.column_dimensions["A"].width = 34
    for col in "BCD":
        ws.column_dimensions[col].width = 14
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
