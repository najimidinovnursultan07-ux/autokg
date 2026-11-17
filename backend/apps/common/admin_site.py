from django.contrib.admin import AdminSite


class AutoKGAdminSite(AdminSite):
    site_header = "AutoKG"
    site_title = "AutoKG — администрирование"
    index_title = "Управление маркетплейсом"

    def has_permission(self, request):
        user = request.user
        return bool(
            user.is_active
            and user.is_staff
            and getattr(user, "role", None) == "admin"
        )
