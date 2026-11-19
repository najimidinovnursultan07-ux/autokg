from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_add_dealer_fk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("user", "Пользователь (устаревшая роль)"),
                    ("dealer", "Менеджер автосалона"),
                    ("admin", "Администратор"),
                ],
                default="user",
                max_length=16,
                verbose_name="Роль",
            ),
        ),
    ]
