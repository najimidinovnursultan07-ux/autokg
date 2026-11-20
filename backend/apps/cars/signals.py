"""
Жизненный цикл медиафайлов в хранилище (Supabase Storage в production):

- pre_save: новое фото машины сжимается в WebP (до 1280px, качество 80) и получает превью
  400×300; логотип салона — до 400px; фото профиля — до 512px.
- post_delete: файлы удаляются из бакета (remove([path])) только после
  успешного commit. Срабатывает и при каскадном удалении машины или салона.
В data-миграциях сигналы не вызываются, поэтому существующие файлы не трогаются.
"""
import logging

from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from apps.accounts.models import User
from apps.common.images import (
    AVATAR_MAX_SIDE,
    LOGO_MAX_SIDE,
    make_thumbnail,
    optimize_image,
)
from apps.dealers.models import Dealer

from .models import CarImage

logger = logging.getLogger(__name__)


def delete_stored_file(storage, name):
    if not name:
        return

    def _delete():
        try:
            storage.delete(name)
        except Exception:  # сбой хранилища не должен ломать удаление объявления
            logger.exception("Не удалось удалить файл %s из хранилища", name)

    transaction.on_commit(_delete)


def _is_new_upload(field_file):
    return bool(field_file) and not getattr(field_file, "_committed", True)


@receiver(pre_save, sender=CarImage, dispatch_uid="carimage_optimize")
def carimage_optimize(sender, instance, raw=False, **kwargs):
    if raw or not _is_new_upload(instance.image):
        return
    source = instance.image.file
    instance.thumbnail = make_thumbnail(source)
    instance.image = optimize_image(source)


@receiver(pre_save, sender=Dealer, dispatch_uid="dealer_logo_optimize")
def dealer_logo_optimize(sender, instance, raw=False, **kwargs):
    if raw or not _is_new_upload(instance.logo):
        return
    instance.logo = optimize_image(instance.logo.file, max_side=LOGO_MAX_SIDE)


@receiver(pre_save, sender=User, dispatch_uid="user_photo_optimize")
def user_photo_optimize(sender, instance, raw=False, **kwargs):
    if raw or not _is_new_upload(instance.profile_photo):
        return
    instance.profile_photo = optimize_image(instance.profile_photo.file, max_side=AVATAR_MAX_SIDE)


@receiver(post_delete, sender=CarImage, dispatch_uid="carimage_delete_file")
def carimage_delete_file(sender, instance, **kwargs):
    delete_stored_file(instance.image.storage, instance.image.name)
    if instance.thumbnail:
        delete_stored_file(instance.thumbnail.storage, instance.thumbnail.name)


@receiver(post_delete, sender=Dealer, dispatch_uid="dealer_delete_logo")
def dealer_delete_logo(sender, instance, **kwargs):
    if instance.logo:
        delete_stored_file(instance.logo.storage, instance.logo.name)


@receiver(post_delete, sender=User, dispatch_uid="user_delete_photo")
def user_delete_photo(sender, instance, **kwargs):
    if instance.profile_photo:
        delete_stored_file(instance.profile_photo.storage, instance.profile_photo.name)
