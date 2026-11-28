"""
Уведомления покупателям через Telegram-бота — без регистрации на сайте.

Покупатель нажимает кнопку на сайте → создаётся подписка с одноразовым токеном
→ ссылка t.me/<бот>?start=<токен> → бот получает /start и привязывает подписку к чату.
"""
import secrets

from django.db import models


def new_token():
    return secrets.token_urlsafe(16)  # 22 символа: A-Z a-z 0-9 _ -


class TelegramChat(models.Model):
    chat_id = models.BigIntegerField("ID чата", unique=True)
    username = models.CharField("Username", max_length=64, blank=True)
    first_name = models.CharField("Имя", max_length=128, blank=True)
    is_blocked = models.BooleanField("Заблокировал бота", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Чат Telegram"
        verbose_name_plural = "Чаты Telegram"

    def __str__(self):
        return f"@{self.username}" if self.username else str(self.chat_id)


class SavedSearch(models.Model):
    """Подписка на новые объявления по фильтрам каталога."""

    chat = models.ForeignKey(
        TelegramChat, on_delete=models.CASCADE, null=True, blank=True, related_name="searches"
    )
    token = models.CharField(max_length=32, unique=True, default=new_token)
    filters = models.JSONField("Фильтры", default=dict, blank=True)
    title = models.CharField("Описание", max_length=200)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Присылаем только объявления, опубликованные после подписки
    subscribed_at = models.DateTimeField("Подписка с", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Подписка на поиск"
        verbose_name_plural = "Подписки на поиск"

    def __str__(self):
        return self.title


class SearchMatch(models.Model):
    """Какие объявления уже отправлены по подписке — чтобы не присылать дважды."""

    search = models.ForeignKey(SavedSearch, on_delete=models.CASCADE, related_name="matches")
    car = models.ForeignKey("cars.Car", on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("search", "car"), name="unique_search_match"),
        ]


class PriceWatch(models.Model):
    """Слежение за ценой конкретного объявления."""

    chat = models.ForeignKey(
        TelegramChat, on_delete=models.CASCADE, null=True, blank=True, related_name="watches"
    )
    token = models.CharField(max_length=32, unique=True, default=new_token)
    car = models.ForeignKey("cars.Car", on_delete=models.CASCADE, related_name="price_watches")
    last_price = models.DecimalField("Последняя цена", max_digits=14, decimal_places=2)
    currency = models.CharField("Валюта", max_length=3)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Слежение за ценой"
        verbose_name_plural = "Слежение за ценой"

    def __str__(self):
        return f"{self.car_id}: {self.last_price} {self.currency}"
