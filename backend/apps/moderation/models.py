from django.conf import settings
from django.db import models


class ModerationEvent(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = "submitted", "Отправлено на модерацию"
        APPROVED = "approved", "Одобрено"
        REJECTED = "rejected", "Отклонено"
        DEACTIVATED = "deactivated", "Снято с публикации"
        REMOVED = "removed", "Удалено"

    car = models.ForeignKey(
        "cars.Car",
        on_delete=models.PROTECT,
        related_name="moderation_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="moderation_events",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.action}: {self.car_id}"
