import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial_payments"),
        ("cars", "0010_initial_dealers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="car",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="payments",
                to="cars.car",
            ),
        ),
        migrations.AlterField(
            model_name="promotion",
            name="car",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="promotions",
                to="cars.car",
            ),
        ),
    ]
