"""Справочник марок и моделей для мото, муравьёв, велосипедов и самокатов."""
from django.db import migrations
from django.utils.text import slugify

CATALOG = {
    "moto": {
        "Honda": ["Dio", "Tact", "Lead", "CB 125", "CBR 250R", "CBR 600RR", "Africa Twin"],
        "Yamaha": ["Jog", "Gear", "YBR 125", "R15", "R1", "MT-07"],
        "Suzuki": ["Address", "GSX-R 600", "V-Strom 650"],
        "Kawasaki": ["Ninja 400", "Z650", "KLX 250"],
        "Stels": ["Flex 250", "Trigger 50", "Tactic 50"],
        "Racer": ["Tiger 150", "Magnum 200", "Panther"],
        "Lifan": ["LF125", "LF150", "KP200"],
        "Zongshen": ["ZS150", "ZS250"],
        "Альфа": ["Alpha 110", "Alpha RX 125"],
        "Другая марка": ["Другой мотоцикл", "Другой мопед"],
    },
    "muravey": {
        "Zongshen": ["Грузовой трицикл 200", "Грузовой трицикл 250"],
        "Lifan": ["LF200ZH", "LF250ZH"],
        "Loncin": ["LX200ZH", "LX250ZH"],
        "Муравей": ["ТГА-200", "Электро-муравей"],
        "Другая марка": ["Другой муравей"],
    },
    "bicycle": {
        "Giant": ["Talon", "ATX", "Escape"],
        "Trek": ["Marlin", "FX", "Domane"],
        "Merida": ["Big.Nine", "Matts", "Scultura"],
        "Stels": ["Navigator", "Pilot", "Focus"],
        "Forward": ["Sporting", "Apache", "Dakota"],
        "Cube": ["Aim", "Attention", "Reaction"],
        "Другая марка": ["Другой велосипед", "Другой электровелосипед"],
    },
    "scooter": {
        "Xiaomi": ["Electric Scooter 4", "Electric Scooter 4 Pro", "Electric Scooter 3 Lite"],
        "Segway-Ninebot": ["Max G30", "E2", "F2"],
        "Kugoo": ["Kirin M4", "S3", "G2 Pro"],
        "Dualtron": ["Mini", "Thunder"],
        "Другая марка": ["Другой самокат"],
    },
}

TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def make_slug(value):
    return slugify(value.lower().translate(TRANSLIT))


def seed(apps, schema_editor):
    Brand = apps.get_model("cars", "Brand")
    Model = apps.get_model("cars", "Model")
    for vehicle_type, brands in CATALOG.items():
        for brand_name, model_names in brands.items():
            brand = Brand.objects.filter(name=brand_name).first()
            if brand is None:
                brand = Brand.objects.create(name=brand_name, slug=make_slug(brand_name))
            for model_name in model_names:
                if Model.objects.filter(brand=brand, name=model_name).exists():
                    continue
                slug = make_slug(model_name)
                if Model.objects.filter(brand=brand, slug=slug).exists():
                    slug = f"{slug}-{vehicle_type}"
                Model.objects.create(brand=brand, name=model_name, slug=slug, vehicle_type=vehicle_type)


class Migration(migrations.Migration):

    dependencies = [
        ("cars", "0019_vehicle_types"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
