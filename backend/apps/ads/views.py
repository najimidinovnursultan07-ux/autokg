from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.permissions import IsAutoBuyAdmin

from .models import AdBanner
from .serializers import AdminAdSerializer, PublicAdSerializer
from .services import (
    banner_stats,
    banner_stats_xlsx,
    parse_stats_period,
    record_click,
    record_impressions,
)

MAX_IMPRESSION_IDS = 10
CLICK_DEDUP_SECONDS = 10 * 60


class PublicAdView(APIView):
    """Публичный API рекламы: без авторизации и со своими лимитами (не тратят общий лимит anon)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)


class AdListView(PublicAdView):
    """Все баннеры, которые показываются сегодня (сайт выбирает нужные по placement)."""

    throttle_scope = "ads"

    def get(self, request):
        banners = AdBanner.objects.live().order_by("placement", "-priority", "id")
        response = Response(PublicAdSerializer(banners, many=True, context={"request": request}).data)
        response["Cache-Control"] = "no-cache"  # браузер всегда спрашивает свежие баннеры
        return response


class ImpressionsSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=MAX_IMPRESSION_IDS
    )


class AdImpressionsView(PublicAdView):
    """POST {"ids": [1, 2]} — баннеры, которые посетитель увидел на экране."""

    throttle_scope = "ad_events"

    def post(self, request):
        serializer = ImpressionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = set(serializer.validated_data["ids"])
        live_ids = list(AdBanner.objects.live().filter(pk__in=ids).values_list("pk", flat=True))
        record_impressions(live_ids)
        return Response(status=204)


class AdClickView(APIView):
    """
    Переход по баннеру: считает клик и перенаправляет на сайт рекламодателя.
    Повторные клики с одного IP по одному баннеру за 10 минут не считаются.
    Без лимита запросов: посетитель всегда должен попасть на сайт рекламодателя.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = ()

    def get(self, request, pk):
        banner = get_object_or_404(AdBanner, pk=pk)
        if banner.is_live:
            ident = BaseThrottle().get_ident(request)
            if cache.add(f"ad-click:{banner.pk}:{ident}", 1, CLICK_DEDUP_SECONDS):
                record_click(banner.pk)
        response = HttpResponseRedirect(banner.link_url)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "origin"
        return response


class AdminAdViewSet(viewsets.ModelViewSet):
    """Админка: баннеры рекламодателей, статистика и выгрузка отчёта в Excel."""

    permission_classes = (IsAutoBuyAdmin,)
    serializer_class = AdminAdSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = None
    filter_backends = ()

    def get_queryset(self):
        queryset = AdBanner.objects.all()
        placement = self.request.query_params.get("placement")
        if placement:
            queryset = queryset.filter(placement=placement)
        return queryset

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        banner = self.get_object()
        start, end = parse_stats_period(request.query_params, banner)
        return Response(banner_stats(banner, start, end))

    @action(detail=True, methods=["get"], url_path="stats/export")
    def stats_export(self, request, pk=None):
        banner = self.get_object()
        start, end = parse_stats_period(request.query_params, banner)
        content = banner_stats_xlsx(banner, banner_stats(banner, start, end))
        response = HttpResponse(
            content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="autobuy-ad-{banner.pk}-{start:%Y-%m-%d}_{end:%Y-%m-%d}.xlsx"'
        )
        return response
