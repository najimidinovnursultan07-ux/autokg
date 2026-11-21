from django.core.management.base import BaseCommand

from apps.subscriptions.notifications import send_subscription_reminders


class Command(BaseCommand):
    help = "Напоминания об окончании тарифов (запускать раз в день)."

    def handle(self, *args, **options):
        from apps.stats.services import purge_old_stats

        result = send_subscription_reminders()
        removed = purge_old_stats()  # хранение статистики салонов — 12 месяцев
        self.stdout.write(
            f"Заканчиваются: {result['expiring']}, закончились: {result['expired']}, "
            f"новых заявок: {result['new_requests']}, удалено старой статистики: {removed}"
        )
