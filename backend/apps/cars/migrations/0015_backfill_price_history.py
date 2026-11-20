from django.db import migrations


def backfill(apps, schema_editor):
    Car = apps.get_model("cars", "Car")
    CarPriceHistory = apps.get_model("cars", "CarPriceHistory")
    existing = set(CarPriceHistory.objects.values_list("car_id", flat=True))
    CarPriceHistory.objects.bulk_create(
        [
            CarPriceHistory(
                car_id=car.pk,
                price=car.price,
                currency=car.currency,
                created_at=car.published_at or car.created_at,
            )
            for car in Car.objects.only("pk", "price", "currency", "published_at", "created_at").iterator()
            if car.pk not in existing
        ],
        batch_size=500,
    )


class Migration(migrations.Migration):
    dependencies = [("cars", "0014_contact_stats_price_history")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
