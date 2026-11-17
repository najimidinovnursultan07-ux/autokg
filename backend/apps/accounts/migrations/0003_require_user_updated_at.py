from django.db import migrations, models
from django.utils import timezone


def backfill_user_updated_at(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    now = timezone.now()
    database = schema_editor.connection.alias
    User.objects.using(database).filter(updated_at__isnull=True).update(
        updated_at=now
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_favorite_cars_user_updated_at"),
        ("cars", "0003_backfill_timestamps_and_seed_cities"),
    ]

    operations = [
        migrations.RunPython(
            backfill_user_updated_at,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
