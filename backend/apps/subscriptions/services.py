"""Бизнес-логика тарифов: текущая подписка, лимиты, бонусы, включение администратором."""
import calendar
from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import PROMOTION_DAYS, TRIAL_DAYS, TRIAL_PLAN_CODE, Plan, Subscription

PROMOTION_TYPES = ("top", "highlight", "urgent")
PROMOTION_LABELS = {"top": "ТОП", "highlight": "Выделение", "urgent": "Срочно"}


def add_months(dt, months):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def month_start(at=None):
    """Начало текущего календарного месяца (по Бишкеку) — с него считаются бонусы."""
    local = timezone.localtime(at or timezone.now())
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def current_subscription(dealer, at=None):
    return (
        Subscription.objects.current(at)
        .filter(dealer=dealer)
        .select_related("plan")
        .order_by("-starts_at")
        .first()
    )


def active_subscription_exists(dealer_ref="dealer"):
    """Exists-выражение для queryset: у салона есть действующий тариф."""
    return Exists(Subscription.objects.current().filter(dealer=OuterRef(dealer_ref)))


def current_plan_subquery(field, dealer_ref="pk"):
    """Поле тарифа текущей подписки салона (для annotate)."""
    return Subquery(
        Subscription.objects.current()
        .filter(dealer=OuterRef(dealer_ref))
        .order_by("-starts_at")
        .values(f"plan__{field}")[:1]
    )


# ── Лимиты и бонусы ────────────────────────────────────────────────────────

def live_cars(dealer):
    """Объявления, которые занимают место в лимите: опубликованы и срок не истёк."""
    from apps.cars.models import Car, not_expired_q

    return Car.objects.filter(dealer=dealer, status=Car.Status.ACTIVE).filter(not_expired_q())


def active_cars_count(dealer):
    return live_cars(dealer).count()


def promotions_used(dealer, at=None):
    from apps.payments.models import Promotion

    start = month_start(at)
    used = {t: 0 for t in PROMOTION_TYPES}
    rows = Promotion.objects.filter(
        car__dealer=dealer, payment__isnull=True, created_at__gte=start
    ).values_list("promotion_type", flat=True)
    for t in rows:
        if t in used:
            used[t] += 1
    return used


def usage(dealer, subscription=None):
    subscription = subscription if subscription is not None else current_subscription(dealer)
    plan = subscription.plan if subscription else None
    used = promotions_used(dealer)
    promotions = {}
    for t in PROMOTION_TYPES:
        limit = plan.quota(t) if plan else 0
        promotions[t] = {
            "label": PROMOTION_LABELS[t],
            "used": used[t],
            "limit": limit,
            "left": None if limit is None else max(limit - used[t], 0),
        }
    return {
        "active_cars": active_cars_count(dealer),
        "max_active_cars": plan.max_active_cars if plan else 0,
        "promotions": promotions,
        "period_start": month_start(),
    }


def ensure_can_publish(dealer, *, exclude_car_id=None):
    """
    Вызывается внутри transaction.atomic() перед тем, как сделать объявление активным.
    Блокирует строку салона, чтобы параллельные запросы не превысили лимит.
    """
    from apps.cars.models import Car
    from apps.dealers.models import Dealer

    Dealer.objects.select_for_update().get(pk=dealer.pk)
    subscription = current_subscription(dealer)
    if subscription is None:
        raise ValidationError({
            "status": "Тариф не активен — публиковать объявления нельзя. "
                      "Сохраните объявление скрытым и подключите тариф в разделе «Мой тариф».",
            "code": "no_subscription",
        })
    qs = live_cars(dealer)
    if exclude_car_id:
        qs = qs.exclude(pk=exclude_car_id)
    limit = subscription.plan.max_active_cars
    if qs.count() >= limit:
        raise ValidationError({
            "status": f"Достигнут лимит тарифа «{subscription.plan.name}»: {limit} активных объявлений. "
                      "Снимите с публикации проданные машины или перейдите на тариф выше.",
            "code": "limit_reached",
        })


@transaction.atomic
def use_promotion(dealer, car, promotion_type):
    from apps.cars.models import Car
    from apps.dealers.models import Dealer
    from apps.payments.models import Promotion

    if promotion_type not in PROMOTION_TYPES:
        raise ValidationError({"promotion_type": "Неизвестный тип продвижения."})
    Dealer.objects.select_for_update().get(pk=dealer.pk)
    if car.dealer_id != dealer.pk:
        raise ValidationError({"detail": "Это объявление принадлежит другому автосалону."})
    if car.status != Car.Status.ACTIVE:
        raise ValidationError({"detail": "Продвигать можно только опубликованное объявление."})
    if car.is_expired:
        raise ValidationError({"detail": "Срок размещения истёк — сначала продлите объявление."})

    subscription = current_subscription(dealer)
    if subscription is None:
        raise ValidationError({"detail": "Тариф не активен. Подключите тариф в разделе «Мой тариф»."})

    now = timezone.now()
    if Promotion.objects.filter(
        car=car, promotion_type=promotion_type, is_active=True, expires_at__gt=now
    ).exists():
        raise ValidationError({"detail": "Это продвижение у объявления уже действует."})

    limit = subscription.plan.quota(promotion_type)
    if limit is not None and promotions_used(dealer)[promotion_type] >= limit:
        raise ValidationError({
            "detail": f"Бонусы «{PROMOTION_LABELS[promotion_type]}» на этот месяц закончились. "
                      "Они обновятся 1-го числа, или перейдите на тариф выше.",
        })

    return Promotion.objects.create(
        car=car,
        promotion_type=promotion_type,
        starts_at=now,
        expires_at=now + timedelta(days=PROMOTION_DAYS),
        is_active=True,
    )


# ── Включение тарифа администратором ───────────────────────────────────────

def _cut_future(dealer, now):
    """Завершает текущую подписку сейчас и удаляет запланированные."""
    Subscription.objects.filter(dealer=dealer, starts_at__gt=now).delete()
    for sub in Subscription.objects.filter(dealer=dealer, starts_at__lte=now, expires_at__gt=now):
        sub.expires_at = max(now, sub.starts_at + timedelta(seconds=1))
        sub.save(update_fields=("expires_at",))


@transaction.atomic
def activate_subscription(dealer, plan, months, *, by=None, amount=None, payment_method="", note=""):
    """
    Тот же тариф — продление: новый период начинается после окончания последнего.
    Другой тариф — замена: текущий заканчивается сейчас, новый начинается сразу.
    """
    from apps.dealers.models import Dealer

    Dealer.objects.select_for_update().get(pk=dealer.pk)
    now = timezone.now()
    last = (
        Subscription.objects.filter(dealer=dealer, expires_at__gt=now)
        .order_by("-expires_at")
        .first()
    )
    if last and last.plan_id == plan.pk:
        starts_at = last.expires_at
    else:
        _cut_future(dealer, now)
        starts_at = now
    return Subscription.objects.create(
        dealer=dealer,
        plan=plan,
        starts_at=starts_at,
        expires_at=add_months(timezone.localtime(starts_at), months),
        months=months,
        amount=amount,
        payment_method=payment_method,
        note=note,
        created_by=by,
    )


@transaction.atomic
def deactivate_subscription(dealer):
    from apps.dealers.models import Dealer

    Dealer.objects.select_for_update().get(pk=dealer.pk)
    _cut_future(dealer, timezone.now())


def start_trial(dealer):
    plan = Plan.objects.filter(code=TRIAL_PLAN_CODE).first()
    if plan is None:
        return None
    now = timezone.now()
    return Subscription.objects.create(
        dealer=dealer,
        plan=plan,
        starts_at=now,
        expires_at=now + timedelta(days=TRIAL_DAYS),
        is_trial=True,
        note="Пробный период",
    )
