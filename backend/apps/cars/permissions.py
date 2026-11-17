from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Car


class CarPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj: Car):
        if (
            request.user.is_staff
            and getattr(request.user, "role", None) == "admin"
        ):
            return True
        if request.method in SAFE_METHODS:
            return (
                obj.status == Car.Status.PUBLISHED
                or obj.owner_id == request.user.pk
            )
        return obj.owner_id == request.user.pk
