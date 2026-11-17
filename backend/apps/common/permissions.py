from rest_framework.permissions import BasePermission


class IsAutoKGAdmin(BasePermission):
    message = "Доступ разрешён только администраторам AutoKG."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_staff
            and getattr(user, "role", None) == "admin"
        )
