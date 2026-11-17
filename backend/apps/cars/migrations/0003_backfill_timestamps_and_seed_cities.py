from django.db import migrations, models
from django.utils import timezone


CITIES = (
    ("Баткен", "batken"),
    ("Балыкчы", "balykchy"),
    ("Бишкек", "bishkek"),
    ("Джалал-Абад", "jalal-abad"),
    ("Кант", "kant"),
    ("Кара-Балта", "kara-balta"),
    ("Каракол", "karakol"),
    ("Кызыл-Кия", "kyzyl-kiya"),
    ("Нарын", "naryn"),
    ("Ош", "osh"),
    ("Талас", "talas"),
    ("Токмок", "tokmok"),
    ("Узген", "uzgen"),
    ("Чолпон-Ата", "cholpon-ata"),
)


def backfill_timestamps_and_seed_cities(apps, schema_editor):
    database = schema_editor.connection.alias
    now = timezone.now()
    for model_name in ("Brand", "Model", "City", "CarImage"):
        model = apps.get_model("cars", model_name)
        model.objects.using(database).filter(
            created_at__isnull=True
        ).update(created_at=now)
        model.objects.using(database).filter(
            updated_at__isnull=True
        ).update(updated_at=now)

    City = apps.get_model("cars", "City")
    for name, slug in CITIES:
        City.objects.using(database).get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "created_at": now,
                "updated_at": now,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("cars", "0002_model_remove_vehiclemodel_brand_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_timestamps_and_seed_cities,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="brand",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="brand",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="model",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="model",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="city",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="city",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="carimage",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="car",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
