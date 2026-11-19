"""Шаг 1/3: схема. Убираем старый CHECK по статусам, добавляем currency и color."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0010_initial_dealers"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="car", name="car_status_is_valid"),
        migrations.AlterField(
            model_name="car",
            name="status",
            field=models.CharField(
                choices=[("active", "Активно"), ("hidden", "Скрыто"), ("sold", "Продано")],
                db_index=True,
                default="active",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="car",
            name="currency",
            field=models.CharField(
                choices=[("KGS", "сом"), ("USD", "$")], default="KGS", max_length=3
            ),
        ),
        migrations.AddField(
            model_name="car",
            name="color",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterModelOptions(
            name="carimage",
            options={
                "ordering": ("position", "id"),
                "verbose_name": "Фото автомобиля",
                "verbose_name_plural": "Фото автомобилей",
            },
        ),
    ]
