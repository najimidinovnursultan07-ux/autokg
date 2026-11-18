from rest_framework.permissions import BasePermission


class IsCarOwner(BasePermission):
    """Только владелец автомобиля может создать платёж."""

    def has_object_permission(self, request, view, obj):
        return obj.owner_id == request.user.pk
