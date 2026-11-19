from django.db import models
from django.utils.text import slugify


def dealer_logo_upload_to(instance, filename):
    import uuid
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    return f"dealers/logos/{instance.slug}/{uuid.uuid4().hex}{ext}"


class Dealer(models.Model):
    name = models.CharField("Название", max_length=200)
    slug = models.SlugField("Slug", max_length=220, unique=True, blank=True)
    logo = models.ImageField(
        "Логотип",
        upload_to=dealer_logo_upload_to,
        blank=True,
        null=True,
    )
    description = models.TextField("Описание", blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=20, blank=True)
    address = models.CharField("Адрес", max_length=300, blank=True)
    city = models.ForeignKey(
        "cars.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dealers",
        verbose_name="Город",
    )
    is_active = models.BooleanField("Активен", default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Автосалон"
        verbose_name_plural = "Автосалоны"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True)
            slug = base
            n = 1
            while Dealer.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
