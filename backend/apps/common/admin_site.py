from django.contrib.admin import AdminSite


class AutoBuyAdminSite(AdminSite):
    site_header = "AutoBuy"
    site_title = "AutoBuy — администрирование"
    index_title = "Управление маркетплейсом"

    def has_permission(self, request):
        user = request.user
        return bool(
            user.is_active
            and user.is_staff
            and getattr(user, "role", None) == "admin"
        )
