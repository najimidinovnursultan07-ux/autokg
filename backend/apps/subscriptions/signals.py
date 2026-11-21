from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.dealers.models import Dealer

from .services import start_trial


@receiver(post_save, sender=Dealer, dispatch_uid="subscriptions_dealer_trial")
def give_trial_to_new_dealer(sender, instance, created, raw=False, **kwargs):
    """Новый салон сразу получает пробный период, чтобы мог выложить машины."""
    if created and not raw:
        start_trial(instance)
