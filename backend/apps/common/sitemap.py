"""
sitemap.xml для поисковиков: публичные страницы, салоны и активные объявления.

Отдаётся с API (/api/sitemap.xml), а фронт на Vercel проксирует его как
https://<сайт>/sitemap.xml — поисковики видят карту на домене сайта.
"""
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.http import require_GET

CACHE_KEY = "sitemap.xml"
CACHE_SECONDS = 60 * 60

STATIC_PAGES = [
    ("/", "daily", "1.0"),
    ("/catalog", "hourly", "0.9"),
    ("/dealers", "daily", "0.8"),
    ("/pricing", "monthly", "0.5"),
    ("/about", "monthly", "0.3"),
    ("/contacts", "monthly", "0.3"),
]


def _url(loc, lastmod=None, changefreq=None, priority=None):
    parts = [f"<loc>{escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"<lastmod>{lastmod.date().isoformat()}</lastmod>")
    if changefreq:
        parts.append(f"<changefreq>{changefreq}</changefreq>")
    if priority:
        parts.append(f"<priority>{priority}</priority>")
    return f"<url>{''.join(parts)}</url>"


def build_sitemap():
    from apps.cars.views import public_cars_queryset
    from apps.dealers.models import Dealer

    base = settings.FRONTEND_URL.rstrip("/")
    urls = [_url(f"{base}{path}", changefreq=freq, priority=prio) for path, freq, prio in STATIC_PAGES]

    dealers = Dealer.objects.filter(is_active=True).exclude(slug="").values_list("slug", "updated_at")
    urls += [_url(f"{base}/dealers/{slug}", updated, "daily", "0.7") for slug, updated in dealers]

    cars = (
        public_cars_queryset()
        .prefetch_related(None)
        .order_by("-updated_at")
        .values_list("id", "updated_at")
    )
    urls += [_url(f"{base}/cars/{car_id}", updated, "weekly", "0.6") for car_id, updated in cars]

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


@require_GET
def sitemap_view(request):
    xml = cache.get(CACHE_KEY)
    if xml is None:
        xml = build_sitemap()
        cache.set(CACHE_KEY, xml, CACHE_SECONDS)
    response = HttpResponse(xml, content_type="application/xml; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
    return response
