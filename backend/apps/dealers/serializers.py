import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.media import cloudinary_variant, file_url
from apps.common.serializers import MAX_UPLOAD_PHOTO_BYTES, ValidatedImageField

from .models import Dealer

LOGO_TRANSFORM = "f_auto,q_auto,c_limit,w_400"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LogoUrlMixin(serializers.Serializer):
    logo_url = serializers.SerializerMethodField()

    def get_logo_url(self, obj):
        return cloudinary_variant(file_url(obj.logo, self.context.get("request")), LOGO_TRANSFORM)


class DealerSerializer(LogoUrlMixin, serializers.ModelSerializer):
    """Админ: полный CRUD салона."""

    logo = ValidatedImageField(max_size=MAX_UPLOAD_PHOTO_BYTES, required=False, allow_null=True)
    slug = serializers.CharField(max_length=220, required=False, allow_blank=True)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    car_count = serializers.IntegerField(read_only=True, default=0)
    managers_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "logo_url", "description",
            "phone", "whatsapp", "address", "city", "city_name",
            "is_active", "car_count", "managers_count", "created_at",
        )
        read_only_fields = ("id", "car_count", "managers_count", "created_at")

    def validate_slug(self, value):
        value = (value or "").strip().lower()
        if not value:
            return ""  # сгенерируется из названия в Dealer.save()
        if not SLUG_RE.match(value):
            raise serializers.ValidationError(
                "Slug: только латинские буквы, цифры и дефис (например, avto-lider)."
            )
        qs = Dealer.objects.filter(slug=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Салон с таким slug уже существует.")
        return value


class DealerPublicSerializer(LogoUrlMixin, serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)
    car_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo_url", "description",
            "phone", "whatsapp", "address", "city_name", "car_count",
        )


class DealerProfileSerializer(LogoUrlMixin, serializers.ModelSerializer):
    """Менеджер редактирует профиль своего салона. slug и is_active менять нельзя."""

    logo = ValidatedImageField(max_size=MAX_UPLOAD_PHOTO_BYTES, required=False, allow_null=True)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "logo_url", "description",
            "phone", "whatsapp", "address", "city", "city_name", "is_active",
        )
        read_only_fields = ("id", "slug", "is_active")


class ManagerSerializer(serializers.ModelSerializer):
    """Админ: менеджеры салонов (role=dealer)."""

    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    dealer_name = serializers.CharField(source="dealer.name", read_only=True, default=None)
    dealer_is_active = serializers.BooleanField(source="dealer.is_active", read_only=True, default=None)

    class Meta:
        model = User
        fields = (
            "id", "email", "first_name", "last_name", "phone", "is_active",
            "dealer", "dealer_name", "dealer_is_active", "password",
            "last_login", "date_joined",
        )
        read_only_fields = ("id", "last_login", "date_joined")
        extra_kwargs = {"email": {"required": True}}

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate(self, attrs):
        password = attrs.get("password")
        if self.instance is None and not password:
            raise serializers.ValidationError({"password": "Укажите временный пароль."})
        if password:
            try:
                validate_password(password, user=self.instance)
            except Exception as exc:
                raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            role=User.Role.DEALER,
            is_staff=False,
            is_superuser=False,
            **validated_data,
        )

    def update(self, instance, validated_data):
        validated_data.pop("password", None)  # пароль меняется только через reset_password
        return super().update(instance, validated_data)


class PasswordResetByAdminSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)

    def validate_password(self, value):
        validate_password(value, user=self.context.get("user"))
        return value
