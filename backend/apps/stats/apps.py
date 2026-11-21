from django.apps import AppConfig


class StatsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.stats"
    verbose_name = "Статистика салонов"

    def ready(self):
        from . import signals  # noqa: F401
