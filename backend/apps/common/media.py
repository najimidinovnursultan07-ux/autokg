"""Помощники для URL фото в Cloudinary (f_auto, q_auto, ограничение ширины)."""

FULL_TRANSFORM = "f_auto,q_auto,c_limit,w_1600"
THUMB_TRANSFORM = "f_auto,q_auto,c_fill,w_400,h_300"


def cloudinary_variant(url, transform):
    """
    Вставляет трансформацию в URL Cloudinary:
    .../image/upload/v123/media/cars/x.jpg -> .../image/upload/<transform>/v123/media/cars/x.jpg
    Для не-Cloudinary URL (локальная разработка) возвращает URL без изменений.
    """
    if not url or "res.cloudinary.com" not in url or "/image/upload/" not in url:
        return url
    head, tail = url.split("/image/upload/", 1)
    return f"{head}/image/upload/{transform}/{tail}"


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
