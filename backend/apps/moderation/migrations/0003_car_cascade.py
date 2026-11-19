import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("moderation", "0002_alter_moderationevent_action"),
        ("cars", "0010_initial_dealers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="moderationevent",
            name="car",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="moderation_events",
                to="cars.car",
            ),
        ),
    ]
