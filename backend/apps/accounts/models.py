from pathlib import Path
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


def profile_photo_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"profile_photos/{instance.pk}/{uuid.uuid4().hex}{extension}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        if extra_fields.get("role") != User.Role.ADMIN:
            raise ValueError("A superuser must have the admin role.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "user", "Пользователь"
        ADMIN = "admin", "Администратор"

    username = None
    email = models.EmailField("Электронная почта", unique=True)
    phone = models.CharField(
        "Телефон",
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?[0-9]{7,15}$",
                message="Введите телефон в международном формате.",
            )
        ],
    )
    role = models.CharField(
        "Роль",
        max_length=16,
        choices=Role.choices,
        default=Role.USER,
    )
    profile_photo = models.ImageField(
        "Фотография профиля",
        upload_to=profile_photo_upload_to,
        blank=True,
        null=True,
    )
    dealer = models.ForeignKey(
        "dealers.Dealer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managers",
        verbose_name="Автосалон",
    )
    favorite_cars = models.ManyToManyField(
        "cars.Car",
        through="favorites.Favorite",
        related_name="favorited_by_users",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
