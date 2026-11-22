from django.conf import settings


class ClientIPMiddleware:
    """
    Подставляет настоящий IP посетителя в REMOTE_ADDR.

    На Render запросы идут через Cloudflare и балансировщик, а заголовок
    X-Forwarded-For Render не чистит — только дописывает в конец. DRF-лимиты
    (throttling) берут IP из X-Forwarded-For, поэтому злоумышленник мог
    подставлять случайный X-Forwarded-For в каждый запрос и обходить лимит
    попыток входа. CF-Connecting-IP Cloudflare всегда перезаписывает сам,
    подделать его нельзя — берём IP оттуда и убираем X-Forwarded-For.

    Работает только если задан CLIENT_IP_HEADER (в production).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        header = getattr(settings, "CLIENT_IP_HEADER", "")
        self.meta_key = f"HTTP_{header.upper().replace('-', '_')}" if header else ""

    def __call__(self, request):
        if self.meta_key:
            client_ip = request.META.get(self.meta_key, "").strip()
            if client_ip:
                request.META["REMOTE_ADDR"] = client_ip
                request.META.pop("HTTP_X_FORWARDED_FOR", None)
        return self.get_response(request)
