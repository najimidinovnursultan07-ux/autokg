from rest_framework.test import APIClient

from apps.cars.models import CarImage
from apps.common.testing import MarketplaceTestCase, make_image


class CarPhotoUploadTests(MarketplaceTestCase):
    client_class = APIClient

    def test_upload_converts_to_webp_and_creates_thumbnail(self):
        car = self.make_car(self.dealer_a)
        self.client.force_authenticate(self.manager_a)

        response = self.client.post(
            f"/api/dashboard/cars/{car.pk}/photos/",
            {"images": [make_image("photo.jpg", size=(2400, 1800))]},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        photo = CarImage.objects.get(car=car)
        self.assertTrue(photo.image.name.startswith("cars/salon-a/"))
        self.assertTrue(photo.image.name.endswith(".webp"))
        self.assertTrue(photo.thumbnail.name.startswith("cars/salon-a/thumbs/"))
        self.assertTrue(photo.image.storage.exists(photo.image.name))
        self.assertTrue(photo.thumbnail.storage.exists(photo.thumbnail.name))
        self.assertTrue(response.data[0]["thumb"].endswith(photo.thumbnail.name))
        self.assertNotEqual(response.data[0]["url"], response.data[0]["thumb"])

    def test_delete_removes_image_and_thumbnail_from_storage(self):
        car = self.make_car(self.dealer_a)
        self.client.force_authenticate(self.manager_a)
        self.client.post(
            f"/api/dashboard/cars/{car.pk}/photos/",
            {"images": [make_image("photo.jpg")]},
            format="multipart",
        )
        photo = CarImage.objects.get(car=car)
        storage, image_name, thumb_name = photo.image.storage, photo.image.name, photo.thumbnail.name

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(f"/api/dashboard/cars/{car.pk}/photos/{photo.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(storage.exists(image_name))
        self.assertFalse(storage.exists(thumb_name))
