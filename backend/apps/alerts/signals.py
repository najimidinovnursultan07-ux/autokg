from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.cars.models import Car

from .services import (
    WATCHED_FIELDS,
    collect_deleted_car_watchers,
    notify_for_car_in_background,
    run_in_background,
    send_deleted_car_messages,
)


@receiver(post_save, sender=Car, dispatch_uid="alerts_car_changed")
def car_changed(sender, instance, created, update_fields=None, raw=False, **kwargs):
    if raw:
        return
    if update_fields is not None and not (set(update_fields) & WATCHED_FIELDS):
        return  # например, счётчик просмотров — подписчикам неинтересно
    car_id = instance.pk
    transaction.on_commit(lambda: notify_for_car_in_background(car_id))


@receiver(pre_delete, sender=Car, dispatch_uid="alerts_car_deleted")
def car_deleted(sender, instance, **kwargs):
    messages = collect_deleted_car_watchers(instance)
    if messages:
        transaction.on_commit(lambda: run_in_background(send_deleted_car_messages, messages))
