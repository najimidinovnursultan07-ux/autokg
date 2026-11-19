"""Шаг 3/3: dealer NOT NULL, новый CHECK по статусам, индексы price и year."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0012_migrate_statuses_and_legacy_dealer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="car",
            name="dealer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cars",
                to="dealers.dealer",
                verbose_name="Автосалон",
            ),
        ),
        migrations.AddConstraint(
            model_name="car",
            constraint=models.CheckConstraint(
                condition=models.Q(("status__in", ["active", "hidden", "sold"])),
                name="car_status_is_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="car",
            index=models.Index(fields=["price"], name="car_price_idx"),
        ),
        migrations.AddIndex(
            model_name="car",
            index=models.Index(fields=["year"], name="car_year_idx"),
        ),
    ]
