"""
Удаление файлов фото из хранилища (Cloudinary: cloudinary.uploader.destroy через
MediaCloudinaryStorage.delete) при удалении записи CarImage. Срабатывает и при
каскадном удалении машины или салона. Файл удаляется только после успешного commit.
В data-миграциях сигналы не вызываются, поэтому существующие фото не трогаются.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Car, CarImage, CarPriceHistory

logger = logging.getLogger(__name__)


def delete_stored_file(storage, name):
    if not name:
        return

    def _delete():
        try:
            storage.delete(name)
        except Exception:  # сбой Cloudinary не должен ломать удаление объявления
            logger.exception("Не удалось удалить файл %s из хранилища", name)

    transaction.on_commit(_delete)


@receiver(post_delete, sender=CarImage, dispatch_uid="carimage_delete_file")
def carimage_delete_file(sender, instance, **kwargs):
    delete_stored_file(instance.image.storage, instance.image.name)


# ── История цен ────────────────────────────────────────────────────────────

@receiver(pre_save, sender=Car, dispatch_uid="car_remember_old_price")
def car_remember_old_price(sender, instance, raw=False, **kwargs):
    instance._old_price = None
    instance._old_status = None
    instance._old_sold_at = None
    if raw:
        return
    if not instance._state.adding:
        row = Car.objects.filter(pk=instance.pk).values_list("price", "currency", "status", "sold_at").first()
        if row:
            instance._old_price = row[:2]
            instance._old_status, instance._old_sold_at = row[2], row[3]
    # Дата продажи: ставится при переходе в «Продано», снимается при отмене
    if instance.status == Car.Status.SOLD and instance._old_status != Car.Status.SOLD:
        instance.sold_at = timezone.now()
    elif instance.status != Car.Status.SOLD:
        instance.sold_at = None


@receiver(post_save, sender=Car, dispatch_uid="car_record_price_history")
def car_record_price_history(sender, instance, created, raw=False, **kwargs):
    if raw:
        return
    old = getattr(instance, "_old_price", None)
    price = Decimal(str(instance.price))
    if created or old is None or old[0] != price or old[1] != instance.currency:
        CarPriceHistory.objects.create(car=instance, price=instance.price, currency=instance.currency)
