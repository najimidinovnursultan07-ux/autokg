from rest_framework.permissions import BasePermission


class IsCarOwner(BasePermission):
    """Только менеджер салона-владельца автомобиля может создать платёж."""

    def has_object_permission(self, request, view, obj):
        return bool(request.user.dealer_id) and obj.dealer_id == request.user.dealer_id
