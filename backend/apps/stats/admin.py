from django.contrib import admin

from .models import DealerMonthStat, ReportDownload


@admin.register(DealerMonthStat)
class DealerMonthStatAdmin(admin.ModelAdmin):
    list_display = ("dealer", "month", "cars_added", "cars_sold", "views", "phone_views", "whatsapp_clicks")
    list_filter = ("month",)
    search_fields = ("dealer__name",)


@admin.register(ReportDownload)
class ReportDownloadAdmin(admin.ModelAdmin):
    list_display = ("dealer", "report_month", "user", "created_at")
    list_filter = ("report_month",)
