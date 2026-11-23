"""
Пробный период сокращён с 14 до 7 дней: действующим пробным подпискам
срок окончания переносится на starts_at + 7 дней.
"""
from datetime import timedelta

from django.db import migrations
from django.utils import timezone

NEW_TRIAL_DAYS = 7


def shorten_trials(apps, schema_editor):
    Subscription = apps.get_model("subscriptions", "Subscription")
    now = timezone.now()
    for sub in Subscription.objects.filter(is_trial=True, expires_at__gt=now):
        new_expires = sub.starts_at + timedelta(days=NEW_TRIAL_DAYS)
        if new_expires < sub.expires_at:
            sub.expires_at = new_expires
            sub.save(update_fields=["expires_at"])


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0003_reminders_sent"),
    ]

    operations = [
        migrations.RunPython(shorten_trials, migrations.RunPython.noop),
    ]
