from io import BytesIO
from unittest import mock

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from apps.common import storage as storage_module
from apps.common.images import make_thumbnail, optimize_image
from apps.common.storage import SupabaseStorage
from apps.common.testing import make_image

SUPABASE_SETTINGS = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
    "SUPABASE_BUCKET_NAME": "media",
}


@override_settings(**SUPABASE_SETTINGS)
class SupabaseStorageTests(SimpleTestCase):
    def setUp(self):
        storage_module.get_supabase_client.cache_clear()
        self.addCleanup(storage_module.get_supabase_client.cache_clear)
        self.bucket = mock.MagicMock()
        self.bucket.get_public_url.side_effect = (
            lambda path: f"https://abc.supabase.co/storage/v1/object/public/media/{path}?"
        )
        patcher = mock.patch.object(storage_module, "get_bucket", return_value=self.bucket)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_uploads_with_content_type_and_no_overwrite(self):
        content = ContentFile(b"webp-bytes", name="x.webp")
        name = SupabaseStorage().save("cars/salon/abc.webp", content)

        self.assertEqual(name, "cars/salon/abc.webp")
        kwargs = self.bucket.upload.call_args.kwargs
        self.assertEqual(kwargs["path"], "cars/salon/abc.webp")
        self.assertEqual(kwargs["file"], b"webp-bytes")
        self.assertEqual(kwargs["file_options"]["content-type"], "image/webp")
        self.assertEqual(kwargs["file_options"]["upsert"], "false")
        self.bucket.exists.assert_not_called()  # имена уникальны, лишних запросов нет

    def test_url_uses_get_public_url(self):
        self.assertEqual(
            SupabaseStorage().url("cars/salon/abc.webp"),
            "https://abc.supabase.co/storage/v1/object/public/media/cars/salon/abc.webp",
        )
        self.bucket.get_public_url.assert_called_once_with("cars/salon/abc.webp")

    def test_delete_calls_remove_with_path_list(self):
        SupabaseStorage().delete("cars/salon/abc.webp")
        self.bucket.remove.assert_called_once_with(["cars/salon/abc.webp"])

    def test_client_is_created_from_settings(self):
        with mock.patch.object(storage_module, "create_client") as create_client:
            storage_module.get_supabase_client()
        create_client.assert_called_once_with("https://abc.supabase.co", "service-role-key")


class ImageProcessingTests(SimpleTestCase):
    def test_optimize_limits_size_and_converts_to_webp(self):
        result = optimize_image(make_image("big.jpg", size=(4000, 3000)))
        self.assertTrue(result.name.endswith(".webp"))
        with Image.open(BytesIO(result.read())) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (1280, 960))
        self.assertEqual(result.content_type, "image/webp")

    def test_thumbnail_is_cropped_to_exact_size(self):
        result = make_thumbnail(make_image("tall.png", fmt="PNG", size=(500, 1500)))
        with Image.open(BytesIO(result.read())) as image:
            self.assertEqual(image.size, (400, 300))
