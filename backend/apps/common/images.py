"""
Обработка изображений при загрузке (замена трансформаций Cloudinary f_auto/q_auto/w_*).

Оригиналы не хранятся: каждое фото приводится к WebP с ограничением по стороне,
EXIF-поворот применяется, а метаданные (включая GPS) удаляются.
"""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


FULL_MAX_SIDE = 1280  # макс. ширина/высота с сохранением пропорций
THUMB_SIZE = (400, 300)  # было c_fill,w_400,h_300
LOGO_MAX_SIDE = 400  # было c_limit,w_400
AVATAR_MAX_SIDE = 512
WEBP_QUALITY = 80
THUMB_QUALITY = 75


def _open(source):
    if hasattr(source, "seek"):
        source.seek(0)
    image = Image.open(source)
    image = ImageOps.exif_transpose(image)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "transparency" in image.info or image.mode in ("LA", "P") else "RGB")
    return image


def _to_webp(image, name, quality):
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=4)
    stem = Path(name or "image").stem or "image"
    file = ContentFile(buffer.getvalue(), name=f"{stem}.webp")
    file.content_type = "image/webp"
    return file


def optimize_image(source, max_side=FULL_MAX_SIDE, quality=WEBP_QUALITY):
    """Уменьшает изображение до max_side по большей стороне и кодирует в WebP."""
    image = _open(source)
    image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return _to_webp(image, getattr(source, "name", None), quality)


def make_thumbnail(source, size=THUMB_SIZE, quality=THUMB_QUALITY):
    """Превью с обрезкой по центру до точного размера (аналог c_fill)."""
    image = _open(source)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        image = background
    return _to_webp(image, getattr(source, "name", None), quality)
