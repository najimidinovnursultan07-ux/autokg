from rest_framework import serializers

from apps.common.media import FULL_TRANSFORM, cloudinary_variant, file_url
from apps.common.serializers import MAX_UPLOAD_PHOTO_BYTES, ValidatedImageField

from .models import AdBanner
from .services import ctr


class ImageUrlsMixin(serializers.Serializer):
    image_url = serializers.SerializerMethodField()
    mobile_image_url = serializers.SerializerMethodField()

    def _url(self, field_file):
        return cloudinary_variant(file_url(field_file, self.context.get("request")), FULL_TRANSFORM)

    def get_image_url(self, obj):
        return self._url(obj.image)

    def get_mobile_image_url(self, obj):
        return self._url(obj.mobile_image)


class PublicAdSerializer(ImageUrlsMixin, serializers.ModelSerializer):
    """Для сайта: без ссылки (переход идёт через /ads/<id>/click/ — так считаются клики)."""

    class Meta:
        model = AdBanner
        fields = ("id", "placement", "title", "advertiser", "image_url", "mobile_image_url", "priority")


class AdminAdSerializer(ImageUrlsMixin, serializers.ModelSerializer):
    image = ValidatedImageField(max_size=MAX_UPLOAD_PHOTO_BYTES, required=False, write_only=True)
    mobile_image = ValidatedImageField(
        max_size=MAX_UPLOAD_PHOTO_BYTES, required=False, allow_null=True, write_only=True
    )
    remove_mobile_image = serializers.BooleanField(required=False, write_only=True, default=False)
    # В multipart отсутствующий флажок DRF считает False — явный default=True для нового баннера
    is_active = serializers.BooleanField(required=False, default=True)
    placement_label = serializers.CharField(source="get_placement_display", read_only=True)
    is_live = serializers.BooleanField(read_only=True)
    ctr = serializers.SerializerMethodField()

    class Meta:
        model = AdBanner
        fields = (
            "id", "title", "advertiser", "advertiser_contact", "placement", "placement_label",
            "image", "mobile_image", "remove_mobile_image", "image_url", "mobile_image_url",
            "link_url", "starts_on", "ends_on", "is_active", "priority", "is_live",
            "impressions", "clicks", "ctr", "created_at", "updated_at",
        )
        read_only_fields = ("id", "impressions", "clicks", "created_at", "updated_at")

    def get_ctr(self, obj):
        return ctr(obj.impressions, obj.clicks)

    def validate(self, attrs):
        if self.instance is None and not attrs.get("image"):
            raise serializers.ValidationError({"image": "Загрузите картинку баннера."})
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError({"ends_on": "Дата окончания раньше даты начала."})
        if attrs.pop("remove_mobile_image", False) and not attrs.get("mobile_image"):
            attrs["mobile_image"] = None
        return attrs
