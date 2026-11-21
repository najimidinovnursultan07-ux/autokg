"""
Восстанавливает «добавлено» и «продано» за последние 12 месяцев из существующих объявлений.
Просмотры и контакты по месяцам раньше не хранились — они считаются с момента этой миграции.
"""
from datetime import date

from django.db import migrations
from django.utils import timezone


def _month(dt):
    local = timezone.localtime(dt)
    return date(local.year, local.month, 1)


def backfill(apps, schema_editor):
    Car = apps.get_model("cars", "Car")
    DealerMonthStat = apps.get_model("stats", "DealerMonthStat")
    now = timezone.localtime()
    index = now.year * 12 + now.month - 1 - 11
    oldest = date(index // 12, index % 12 + 1, 1)

    counters = {}
    for dealer_id, created_at, sold_at in Car.objects.values_list("dealer_id", "created_at", "sold_at"):
        if created_at and _month(created_at) >= oldest:
            counters.setdefault((dealer_id, _month(created_at)), [0, 0])[0] += 1
        if sold_at and _month(sold_at) >= oldest:
            counters.setdefault((dealer_id, _month(sold_at)), [0, 0])[1] += 1
    DealerMonthStat.objects.bulk_create([
        DealerMonthStat(dealer_id=dealer_id, month=month, cars_added=added, cars_sold=sold)
        for (dealer_id, month), (added, sold) in counters.items()
    ])


class Migration(migrations.Migration):
    dependencies = [
        ("stats", "0001_initial"),
        ("cars", "0017_car_sold_at"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
