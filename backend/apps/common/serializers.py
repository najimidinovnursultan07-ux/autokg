from pathlib import Path

from rest_framework import serializers


MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_IMAGE_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}


class ValidatedImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if data.size > MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError(
                "Размер изображения не должен превышать 10 МБ."
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
