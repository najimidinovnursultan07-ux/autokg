"""
Удаление файлов фото из хранилища (Cloudinary: cloudinary.uploader.destroy через
MediaCloudinaryStorage.delete) при удалении записи CarImage. Срабатывает и при
каскадном удалении машины или салона. Файл удаляется только после успешного commit.
В data-миграциях сигналы не вызываются, поэтому существующие фото не трогаются.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import CarImage

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
