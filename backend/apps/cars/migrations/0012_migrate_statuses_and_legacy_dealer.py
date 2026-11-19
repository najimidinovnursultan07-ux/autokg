"""
Шаг 2/3: данные.

1. Статусы: published → active, sold → sold, draft/pending/rejected/inactive/removed → hidden.
   Ничего не удаляется: бывшие «удалённые» объявления становятся скрытыми,
   администратор может удалить их вручную. Фото в Cloudinary не трогаются.
2. Все машины без салона привязываются к салону «Без салона (старые объявления)».
"""
from django.db import migrations

LEGACY_SLUG = "bez-salona"
LEGACY_NAME = "Без салона (старые объявления)"

STATUS_MAP = {
    "published": "active",
    "sold": "sold",
    "draft": "hidden",
    "pending": "hidden",
    "rejected": "hidden",
    "inactive": "hidden",
    "removed": "hidden",
}


def forwards(apps, schema_editor):
    Car = apps.get_model("cars", "Car")
    Dealer = apps.get_model("dealers", "Dealer")

    for old, new in STATUS_MAP.items():
        Car.objects.filter(status=old).update(status=new)

    if Car.objects.filter(dealer__isnull=True).exists():
        legacy, _ = Dealer.objects.get_or_create(
            slug=LEGACY_SLUG,
            defaults={"name": LEGACY_NAME, "is_active": True},
        )
        Car.objects.filter(dealer__isnull=True).update(dealer=legacy)


def backwards(apps, schema_editor):
    Car = apps.get_model("cars", "Car")
    Car.objects.filter(status="active").update(status="published")
    Car.objects.filter(status="hidden").update(status="inactive")


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0011_status_currency_color"),
        ("dealers", "0001_initial_dealers"),
        ("moderation", "0003_car_cascade"),
        ("payments", "0002_car_on_delete"),
        ("favorites", "0002_alter_favorite_car_alter_favorite_user"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
