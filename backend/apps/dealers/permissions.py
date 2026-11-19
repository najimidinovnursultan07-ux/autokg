from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == "admin" and
            request.user.is_staff
        )


class IsDealerRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == "dealer" and
            request.user.dealer_id is not None and
            request.user.dealer.is_active
        )


class IsDealerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == "admin" and request.user.is_staff:
            return True
        return (
            request.user.role == "dealer" and
            request.user.dealer_id is not None and
            request.user.dealer.is_active
        )
