"""
Снижение цен тарифов «Бизнес» и «Премиум». «Старт» остаётся прежним.
Уже оплаченные подписки не затрагиваются: сумма фиксируется при оплате.
"""
from decimal import Decimal

from django.db import migrations

NEW_PRICES = {
    "business": dict(price_month=Decimal("2100"), price_3_months=Decimal("5670"), price_12_months=Decimal("21000")),
    "premium": dict(price_month=Decimal("5599"), price_3_months=Decimal("15110"), price_12_months=Decimal("55990")),
}

OLD_PRICES = {
    "business": dict(price_month=Decimal("2990"), price_3_months=Decimal("8070"), price_12_months=Decimal("29900")),
    "premium": dict(price_month=Decimal("7990"), price_3_months=Decimal("21570"), price_12_months=Decimal("79900")),
}


def _apply(apps, prices):
    Plan = apps.get_model("subscriptions", "Plan")
    for code, values in prices.items():
        Plan.objects.filter(code=code).update(**values)


def lower_prices(apps, schema_editor):
    _apply(apps, NEW_PRICES)


def restore_prices(apps, schema_editor):
    _apply(apps, OLD_PRICES)


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0004_shorten_active_trials"),
    ]

    operations = [migrations.RunPython(lower_prices, restore_prices)]
