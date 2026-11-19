import os

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = (
        "Создать администратора платформы из переменных окружения "
        "DJANGO_ADMIN_EMAIL и DJANGO_ADMIN_PASSWORD (если он ещё не создан)."
    )

    def handle(self, *args, **kwargs):
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("DJANGO_ADMIN_PASSWORD", "")

        if not email or not password:
            self.stdout.write(
                "DJANGO_ADMIN_EMAIL / DJANGO_ADMIN_PASSWORD не заданы — пропускаю."
            )
            return

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            changed = []
            if user.role != User.Role.ADMIN:
                user.role = User.Role.ADMIN
                changed.append("role")
            if not user.is_staff:
                user.is_staff = True
                changed.append("is_staff")
            if changed:
                user.save(update_fields=changed)
            self.stdout.write(self.style.WARNING(f"Администратор {email} уже существует."))
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Администратор {email} создан."))
