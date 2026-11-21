import re

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.media import cloudinary_variant, file_url
from apps.common.serializers import MAX_UPLOAD_PHOTO_BYTES, ValidatedImageField

from .models import Dealer, DealerReview

LOGO_TRANSFORM = "f_auto,q_auto,c_limit,w_400"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def check_location(attrs, instance=None):
    """Координаты задаются парой: либо обе, либо ни одной."""
    lat = attrs.get("latitude", getattr(instance, "latitude", None))
    lng = attrs.get("longitude", getattr(instance, "longitude", None))
    if (lat is None) != (lng is None):
        raise serializers.ValidationError(
            {"latitude": ["Укажите точку на карте целиком (широта и долгота)."]}
        )


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
    # Админ салона создаётся вместе с салоном (только при создании)
    admin_email = serializers.EmailField(write_only=True, required=False)
    admin_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)
    admin_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=150)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "logo_url", "description",
            "phone", "whatsapp", "address", "latitude", "longitude", "city", "city_name",
            "is_active", "car_count", "managers_count", "created_at",
            "admin_email", "admin_password", "admin_first_name",
        )
        read_only_fields = ("id", "car_count", "managers_count", "created_at")

    def validate(self, attrs):
        check_location(attrs, self.instance)
        if self.instance is not None:
            for key in ("admin_email", "admin_password", "admin_first_name"):
                attrs.pop(key, None)
            return attrs
        errors = {}
        email = (attrs.get("admin_email") or "").strip().lower()
        password = attrs.get("admin_password") or ""
        if not email:
            errors["admin_email"] = ["Укажите email администратора салона."]
        elif User.objects.filter(email__iexact=email).exists():
            errors["admin_email"] = ["Пользователь с таким email уже существует."]
        if not password:
            errors["admin_password"] = ["Укажите пароль администратора салона."]
        else:
            try:
                validate_password(password)
            except Exception as exc:
                errors["admin_password"] = list(getattr(exc, "messages", [str(exc)]))
        if errors:
            raise serializers.ValidationError(errors)
        attrs["admin_email"] = email
        return attrs

    def create(self, validated_data):
        from django.db import transaction

        email = validated_data.pop("admin_email")
        password = validated_data.pop("admin_password")
        first_name = validated_data.pop("admin_first_name", "")
        with transaction.atomic():
            dealer = super().create(validated_data)
            self.created_admin = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                role=User.Role.DEALER,
                dealer=dealer,
            )
        return dealer

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
    rating = serializers.SerializerMethodField()
    reviews_count = serializers.IntegerField(read_only=True, default=0)
    is_verified = serializers.BooleanField(read_only=True, default=False)
    is_featured = serializers.BooleanField(read_only=True, default=False)

    def get_rating(self, obj):
        value = getattr(obj, "rating", None)
        return round(float(value), 1) if value is not None else None

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo_url", "description",
            "phone", "whatsapp", "address", "latitude", "longitude", "city_name", "car_count",
            "rating", "reviews_count", "is_verified", "is_featured",
        )


class DealerProfileSerializer(LogoUrlMixin, serializers.ModelSerializer):
    """Менеджер редактирует профиль своего салона. slug и is_active менять нельзя."""

    logo = ValidatedImageField(max_size=MAX_UPLOAD_PHOTO_BYTES, required=False, allow_null=True)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)

    class Meta:
        model = Dealer
        fields = (
            "id", "name", "slug", "logo", "logo_url", "description",
            "phone", "whatsapp", "address", "latitude", "longitude", "city", "city_name", "is_active",
        )
        read_only_fields = ("id", "slug", "is_active")

    def validate(self, attrs):
        check_location(attrs, self.instance)
        return attrs


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


# ── Отзывы ─────────────────────────────────────────────────────────────────

class DealerReviewSerializer(serializers.ModelSerializer):
    """Публичный отзыв: показываем только имя, оценку, текст и дату."""

    class Meta:
        model = DealerReview
        fields = ("id", "author_name", "rating", "text", "created_at")
        read_only_fields = ("id", "created_at")


class DealerReviewCreateSerializer(serializers.ModelSerializer):
    # Скрытое поле-ловушка для ботов: человек его не видит и не заполняет
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = DealerReview
        fields = ("author_name", "rating", "text", "website")

    def validate_author_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Укажите имя.")
        return value

    def validate_text(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("Напишите хотя бы пару предложений (от 10 символов).")
        return value

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Оценка — от 1 до 5.")
        return value


class AdminDealerReviewSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source="dealer.name", read_only=True)
    dealer_slug = serializers.CharField(source="dealer.slug", read_only=True)

    class Meta:
        model = DealerReview
        fields = (
            "id", "dealer", "dealer_name", "dealer_slug", "author_name",
            "rating", "text", "status", "created_at", "updated_at",
        )
        read_only_fields = tuple(f for f in fields if f != "status")
