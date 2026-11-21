from datetime import timedelta
from decimal import Decimal

from django.db import migrations
from django.utils import timezone

PLANS = [
    dict(
        code="start", name="Старт", sort_order=1,
        price_month=Decimal("990"), price_3_months=Decimal("2670"), price_12_months=Decimal("9900"),
        max_active_cars=10, top_per_month=1, highlight_per_month=2, urgent_per_month=1,
        has_badge=False, stats_level="basic", has_excel_import=False,
        list_priority=0, featured_on_home=False, priority_support=False,
    ),
    dict(
        code="business", name="Бизнес", sort_order=2,
        price_month=Decimal("2990"), price_3_months=Decimal("8070"), price_12_months=Decimal("29900"),
        max_active_cars=30, top_per_month=4, highlight_per_month=10, urgent_per_month=5,
        has_badge=True, stats_level="full", has_excel_import=True,
        list_priority=1, featured_on_home=False, priority_support=False,
    ),
    dict(
        code="premium", name="Премиум", sort_order=3,
        price_month=Decimal("7990"), price_3_months=Decimal("21570"), price_12_months=Decimal("79900"),
        max_active_cars=150, top_per_month=15, highlight_per_month=30, urgent_per_month=None,
        has_badge=True, stats_level="export", has_excel_import=True,
        list_priority=2, featured_on_home=True, priority_support=True,
    ),
]


def seed(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "Plan")
    Subscription = apps.get_model("subscriptions", "Subscription")
    Dealer = apps.get_model("dealers", "Dealer")
    for data in PLANS:
        Plan.objects.update_or_create(code=data["code"], defaults=data)
    # Действующие салоны получают пробный период, чтобы объявления не пропали после выкладки
    business = Plan.objects.get(code="business")
    now = timezone.now()
    Subscription.objects.bulk_create([
        Subscription(
            dealer=dealer, plan=business, starts_at=now, expires_at=now + timedelta(days=14),
            is_trial=True, note="Пробный период (подключение тарифов)",
        )
        for dealer in Dealer.objects.all()
    ])


def unseed(apps, schema_editor):
    apps.get_model("subscriptions", "Subscription").objects.all().delete()
    apps.get_model("subscriptions", "Plan").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
        ("dealers", "0002_location_and_reviews"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
