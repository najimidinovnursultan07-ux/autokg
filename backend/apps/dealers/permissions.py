"""
Права доступа. Все проверки выполняются на бэкенде.

Для неавторизованных запросов DRF возвращает 401 (JWT-аутентификатор отдаёт
заголовок WWW-Authenticate), для авторизованных без прав — 403.
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission


def is_admin(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and getattr(user, "role", None) == "admin"
    )


def is_dealer(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and getattr(user, "role", None) == "dealer"
        and user.dealer_id is not None
    )


class PublicReadOnly(BasePermission):
    """Чтение — всем. Любая запись запрещена (аноним → 401, остальные → 403)."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsAdminRole(BasePermission):
    message = "Доступ разрешён только администратору платформы."

    def has_permission(self, request, view):
        return is_admin(request.user)


class IsDealerRole(BasePermission):
    """Менеджер активного салона. Если салон заблокирован — 403."""

    message = "Доступ разрешён только менеджерам автосалонов."

    def has_permission(self, request, view):
        user = request.user
        if not is_dealer(user):
            return False
        if not user.dealer.is_active:
            self.message = "Ваш автосалон заблокирован. Обратитесь к администратору."
            return False
        return True


class IsDealerOwnerOrAdmin(BasePermission):
    """Объект (Car) принадлежит салону пользователя, либо пользователь — admin."""

    message = "Это объявление принадлежит другому автосалону."

    def has_permission(self, request, view):
        return is_admin(request.user) or IsDealerRole().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True
        dealer_id = getattr(obj, "dealer_id", None)
        return dealer_id is not None and dealer_id == request.user.dealer_id
