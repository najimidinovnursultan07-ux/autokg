from django.core.management.base import BaseCommand

from apps.subscriptions.notifications import send_subscription_reminders


class Command(BaseCommand):
    help = "Напоминания об окончании тарифов (запускать раз в день)."

    def handle(self, *args, **options):
        result = send_subscription_reminders()
        self.stdout.write(
            f"Заканчиваются: {result['expiring']}, закончились: {result['expired']}, "
            f"новых заявок: {result['new_requests']}"
        )
