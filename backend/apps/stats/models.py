"""
Помесячная статистика салонов для раздела «Отчёт».

Каждый месяц считается с нуля (строка на месяц). Данные старше
RETENTION_MONTHS месяцев удаляются (services.purge_old_stats).
"""
from django.conf import settings
from django.db import models

RETENTION_MONTHS = 12
PDF_DOWNLOADS_PER_MONTH = 2


class DealerMonthStat(models.Model):
    dealer = models.ForeignKey(
        "dealers.Dealer", on_delete=models.CASCADE, related_name="month_stats", verbose_name="Автосалон"
    )
    month = models.DateField("Месяц (1-е число)")
    cars_added = models.PositiveIntegerField("Добавлено объявлений", default=0)
    cars_sold = models.PositiveIntegerField("Продано", default=0)
    views = models.PositiveIntegerField("Просмотры", default=0)
    phone_views = models.PositiveIntegerField("Открыли номер", default=0)
    whatsapp_clicks = models.PositiveIntegerField("WhatsApp", default=0)

    class Meta:
        verbose_name = "Статистика салона за месяц"
        verbose_name_plural = "Статистика салонов по месяцам"
        constraints = [models.UniqueConstraint(fields=("dealer", "month"), name="dealer_month_stat_unique")]
        indexes = [models.Index(fields=("month",))]

    def __str__(self):
        return f"{self.dealer} — {self.month:%m.%Y}"


class CarMonthStat(models.Model):
    dealer = models.ForeignKey("dealers.Dealer", on_delete=models.CASCADE, related_name="car_month_stats")
    # SET_NULL: удалили объявление — цифры месяца остаются в отчёте под сохранённым названием
    car = models.ForeignKey("cars.Car", on_delete=models.SET_NULL, null=True, blank=True, related_name="month_stats")
    car_title = models.CharField(max_length=200)
    month = models.DateField()
    views = models.PositiveIntegerField(default=0)
    phone_views = models.PositiveIntegerField(default=0)
    whatsapp_clicks = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("car", "month"), name="car_month_stat_unique")]
        indexes = [models.Index(fields=("dealer", "month"))]


class ReportDownload(models.Model):
    """Журнал скачиваний PDF — для лимита «2 раза в месяц»."""

    dealer = models.ForeignKey("dealers.Dealer", on_delete=models.CASCADE, related_name="report_downloads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    report_month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
