"""
Хранилище медиафайлов в Supabase Storage (официальный клиент ``supabase``).

Django ImageField хранит в БД путь объекта внутри бакета
(например ``cars/salon/3f2a….webp``), а публичная ссылка строится через
``supabase.storage.from_(bucket).get_public_url(path)``.

Переменные окружения: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_BUCKET_NAME.
Бакет должен быть публичным (Storage → Bucket → Public), иначе ссылки не откроются.
Service role key обходит RLS — он используется только на бэкенде.
"""
import logging
import mimetypes
from functools import lru_cache

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from supabase import create_client

logger = logging.getLogger(__name__)

# Имена уникальны (uuid4) и файлы не меняются — кэш на год.
CACHE_CONTROL_SECONDS = "31536000"


@lru_cache(maxsize=1)
def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_bucket():
    return get_supabase_client().storage.from_(settings.SUPABASE_BUCKET_NAME)


def guess_content_type(path, content=None):
    content_type = getattr(content, "content_type", None)
    return content_type or mimetypes.guess_type(path)[0] or "application/octet-stream"


def upload_file(path, data, content_type=None, upsert=False):
    """Загружает байты в бакет и возвращает публичную ссылку."""
    get_bucket().upload(
        path=path,
        file=data,
        file_options={
            "content-type": content_type or guess_content_type(path),
            "cache-control": CACHE_CONTROL_SECONDS,
            "upsert": "true" if upsert else "false",
        },
    )
    return public_url(path)


def public_url(path):
    return get_bucket().get_public_url(path.lstrip("/")).rstrip("?")


def remove_file(path):
    """Удаляет объект: supabase.storage.from_(bucket).remove([path])."""
    get_bucket().remove([path])


def file_exists(path):
    return get_bucket().exists(path)


@deconstructible
class SupabaseStorage(Storage):
    """
    Django-хранилище по умолчанию для ImageField/FileField.

    - save(): upload() с Content-Type и Cache-Control, без перезаписи (upsert=false);
    - delete(): remove([path]);
    - url(): get_public_url(path).
    Уникальные имена (uuid4 + расширение) задают upload_to в моделях, поэтому
    get_available_name не делает лишний сетевой запрос exists().
    """

    def _save(self, name, content):
        name = name.replace("\\", "/").lstrip("/")
        if hasattr(content, "seek"):
            content.seek(0)
        upload_file(name, content.read(), guess_content_type(name, content))
        return name

    def _open(self, name, mode="rb"):
        file = ContentFile(get_bucket().download(name))
        file.name = name
        return file

    def delete(self, name):
        if name:
            remove_file(name)

    def exists(self, name):
        return file_exists(name)

    def url(self, name):
        return public_url(name)

    def size(self, name):
        info = get_bucket().info(name)
        return int(info.get("size") or info.get("metadata", {}).get("size") or 0)

    def get_available_name(self, name, max_length=None):
        name = name.replace("\\", "/")
        return name[:max_length] if max_length else name
