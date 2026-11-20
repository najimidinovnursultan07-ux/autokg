from django.contrib.admin.apps import AdminConfig


class AutoBuyAdminConfig(AdminConfig):
    default_site = "apps.common.admin_site.AutoBuyAdminSite"
