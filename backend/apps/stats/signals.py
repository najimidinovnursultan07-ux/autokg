from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.cars.models import Car

from .services import record_added, record_sold, record_unsold


@receiver(post_save, sender=Car, dispatch_uid="stats_car_added_or_sold")
def track_car_events(sender, instance, created, raw=False, **kwargs):
    """Новое объявление и продажа попадают в статистику месяца.
    Старый статус запоминает pre_save в apps.cars.signals (_old_status/_old_sold_at)."""
    if raw:
        return
    if created:
        record_added(instance)
    old_status = getattr(instance, "_old_status", None)
    is_sold = instance.status == Car.Status.SOLD
    was_sold = old_status == Car.Status.SOLD
    if is_sold and not was_sold:
        record_sold(instance)
    elif was_sold and not is_sold:
        record_unsold(instance, getattr(instance, "_old_sold_at", None))
