from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from apps.common.serializers import ValidatedImageField

from .models import User


class UserSerializer(serializers.ModelSerializer):
    profile_photo = ValidatedImageField(required=False, allow_null=True)
    dealer_id = serializers.IntegerField(source="dealer.id", read_only=True, allow_null=True, default=None)
    dealer_name = serializers.CharField(source="dealer.name", read_only=True, allow_null=True, default=None)
    dealer_slug = serializers.CharField(source="dealer.slug", read_only=True, allow_null=True, default=None)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_staff",
            "profile_photo",
            "dealer_id",
            "dealer_name",
            "dealer_slug",
            "updated_at",
        )
        read_only_fields = ("id", "email", "role", "is_staff", "dealer_id", "dealer_name", "dealer_slug", "updated_at")
        extra_kwargs = {
            "first_name": {"allow_blank": False},
            "last_name": {"allow_blank": False},
            "phone": {"allow_blank": False, "allow_null": False},
        }

    def update(self, instance, validated_data):
        old_photo = instance.profile_photo
        updated_user = super().update(instance, validated_data)
        if (
            old_photo
            and old_photo.name
            and old_photo.name != getattr(updated_user.profile_photo, "name", None)
        ):
            old_photo.delete(save=False)
        return updated_user


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "password_confirmation",
        )
        read_only_fields = ("id",)
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            "phone": {"required": True, "allow_blank": False, "allow_null": False},
        }

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "Пользователь с таким адресом электронной почты уже существует."
            )
        return email

    def validate(self, attrs):
        password = attrs.get("password")
        if password != attrs.pop("password_confirmation", None):
            raise serializers.ValidationError(
                {"password_confirmation": "Пароли не совпадают."}
            )
        validate_password(password, user=User(**attrs))
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirmation"]:
            raise serializers.ValidationError(
                {"new_password_confirmation": "Пароли не совпадают."}
            )

        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (
            TypeError,
            ValueError,
            OverflowError,
            UnicodeDecodeError,
            User.DoesNotExist,
        ):
            raise serializers.ValidationError(
                {"token": "Ссылка восстановления недействительна или устарела."}
            )

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"token": "Ссылка восстановления недействительна или устарела."}
            )

        validate_password(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirmation = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Текущий пароль указан неверно."}
            )
        if attrs["new_password"] != attrs["new_password_confirmation"]:
            raise serializers.ValidationError(
                {"new_password_confirmation": "Пароли не совпадают."}
            )
        validate_password(attrs["new_password"], user=user)
        return attrs
