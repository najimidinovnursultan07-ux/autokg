from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Создать администратора по умолчанию если его ещё нет"

    def handle(self, *args, **kwargs):
        email = "nursultannajimidinov@gmail.com"
        password = "nursultanadmin!"

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"Администратор {email} уже существует."))
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            first_name="Nursultan",
            last_name="Najimidinov",
        )
        self.stdout.write(self.style.SUCCESS(f"Администратор {email} успешно создан."))
