"""Помощники для публичных URL медиафайлов (Supabase Storage или локальный MEDIA_URL)."""


def file_url(field_file, request=None):
    if not field_file:
        return None
    try:
        url = field_file.url
    except ValueError:
        return None
    if request is not None and url.startswith("/"):
        url = request.build_absolute_uri(url)
    return url
