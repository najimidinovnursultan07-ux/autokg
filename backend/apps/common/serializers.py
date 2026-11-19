from pathlib import Path

from rest_framework import serializers


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MAX_UPLOAD_PHOTO_BYTES = 5 * 1024 * 1024  # фото машин и логотипы салонов
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_IMAGE_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}


class ValidatedImageField(serializers.ImageField):
    """Проверяет формат по содержимому (Pillow), размер и разрешение."""

    def __init__(self, *args, max_size=MAX_IMAGE_SIZE_BYTES, **kwargs):
        self.max_size = max_size
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        if getattr(data, "size", 0) > self.max_size:
            raise serializers.ValidationError(
                f"Размер изображения не должен превышать {self.max_size // (1024 * 1024)} МБ."
            )

        image = super().to_internal_value(data)
        image_format = image.image.format
        extension = Path(image.name).suffix.lower()
        if (
            image_format not in ALLOWED_IMAGE_FORMATS
            or extension not in ALLOWED_IMAGE_EXTENSIONS[image_format]
        ):
            raise serializers.ValidationError(
                "Файл должен быть изображением JPEG/JPG, PNG или WEBP "
                "с соответствующим расширением."
            )
        if image.image.width * image.image.height > MAX_IMAGE_PIXELS:
            raise serializers.ValidationError(
                "Разрешение изображения не должно превышать 40 мегапикселей."
            )
        image.seek(0)
        return image
