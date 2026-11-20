"""
Одноразовый перенос уже загруженных файлов из Cloudinary в Supabase Storage.

Файлы копируются под тем же путём, что записан в БД (например
``media/cars/salon/3f2a…_ab12cd``), поэтому записи в PostgreSQL менять не нужно:
после переключения хранилища ссылку вернёт get_public_url(путь).
Для фото машин без превью дополнительно создаётся thumbnail 400×300.

    python manage.py migrate_media_to_supabase --cloud-name <имя> --dry-run
    python manage.py migrate_media_to_supabase --cloud-name <имя>

Cloudinary SDK не нужен: файлы скачиваются по публичному URL доставки.
"""
import mimetypes
import os
from io import BytesIO
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from apps.accounts.models import User
from apps.cars.models import CarImage, car_thumbnail_upload_to
from apps.common.images import make_thumbnail
from apps.common.storage import file_exists, upload_file
from apps.dealers.models import Dealer

PIL_CONTENT_TYPES = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}


def detect_content_type(key, data, header_value):
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format in PIL_CONTENT_TYPES:
                return PIL_CONTENT_TYPES[image.format]
    except Exception:
        pass
    if header_value and header_value.startswith("image/"):
        return header_value.split(";")[0]
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


class Command(BaseCommand):
    help = "Скопировать медиафайлы из Cloudinary в Supabase Storage под теми же путями."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cloud-name",
            default=os.environ.get("CLOUDINARY_CLOUD_NAME", ""),
            help="Имя облака Cloudinary (или переменная CLOUDINARY_CLOUD_NAME).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет сделано.")
        parser.add_argument("--overwrite", action="store_true", help="Перезаписать файлы, уже лежащие в бакете.")
        parser.add_argument("--timeout", type=int, default=30)

    def handle(self, *args, **options):
        if not settings.USE_SUPABASE_STORAGE:
            raise CommandError("Supabase Storage не настроен: задайте SUPABASE_* переменные окружения.")
        if not options["cloud_name"]:
            raise CommandError("Укажите --cloud-name или CLOUDINARY_CLOUD_NAME.")

        self.base_url = f"https://res.cloudinary.com/{options['cloud_name']}/image/upload"
        self.dry_run = options["dry_run"]
        self.overwrite = options["overwrite"]
        self.timeout = options["timeout"]
        self.stats = {"copied": 0, "skipped": 0, "thumbs": 0, "failed": 0}

        for image in CarImage.objects.select_related("car__dealer").iterator():
            data = self.copy(image.image.name)
            if not image.thumbnail:
                self.add_thumbnail(image, data)
        for dealer in Dealer.objects.exclude(logo="").exclude(logo__isnull=True).iterator():
            self.copy(dealer.logo.name)
        for user in User.objects.exclude(profile_photo="").exclude(profile_photo__isnull=True).iterator():
            self.copy(user.profile_photo.name)

        style = self.style.WARNING if self.stats["failed"] else self.style.SUCCESS
        self.stdout.write(style(
            "Готово{}: скопировано {copied}, пропущено {skipped}, превью {thumbs}, ошибок {failed}.".format(
                " (dry-run)" if self.dry_run else "", **self.stats
            )
        ))

    def download(self, key):
        request = Request(f"{self.base_url}/{quote(key)}", headers={"User-Agent": "media-migration/1.0"})
        with urlopen(request, timeout=self.timeout) as response:
            return response.read(), response.headers.get("Content-Type", "")

    def copy(self, key):
        """Копирует объект; возвращает байты файла (для превью) или None."""
        if not key:
            return None
        try:
            if not self.overwrite and file_exists(key):
                self.stats["skipped"] += 1
                return None
            if self.dry_run:
                self.stdout.write(f"  copy {key}")
                self.stats["copied"] += 1
                return None
            data, header_type = self.download(key)
            upload_file(key, data, detect_content_type(key, data, header_type), upsert=self.overwrite)
            self.stats["copied"] += 1
            self.stdout.write(f"  ok   {key}")
            return data
        except Exception as exc:
            self.stats["failed"] += 1
            self.stderr.write(f"  fail {key}: {exc}")
            return None

    def add_thumbnail(self, image, data):
        if self.dry_run:
            self.stdout.write(f"  thumb для фото #{image.pk}")
            self.stats["thumbs"] += 1
            return
        try:
            if data is None:
                data, _ = self.download(image.image.name)
            thumb = make_thumbnail(BytesIO(data))
            key = car_thumbnail_upload_to(image, thumb.name)
            upload_file(key, thumb.read(), "image/webp")
            CarImage.objects.filter(pk=image.pk).update(thumbnail=key)
            self.stats["thumbs"] += 1
        except Exception as exc:
            self.stats["failed"] += 1
            self.stderr.write(f"  fail thumb #{image.pk}: {exc}")
