from django.db import migrations


VEHICLE_CATALOG = (
    (
        "Acura",
        "acura",
        (("MDX", "mdx"), ("RDX", "rdx"), ("TLX", "tlx")),
    ),
    (
        "Audi",
        "audi",
        (("A3", "a3"), ("A4", "a4"), ("A6", "a6"), ("Q5", "q5"), ("Q7", "q7")),
    ),
    (
        "BMW",
        "bmw",
        (
            ("3 Series", "3-series"),
            ("5 Series", "5-series"),
            ("X3", "x3"),
            ("X5", "x5"),
            ("X6", "x6"),
        ),
    ),
    ("BYD", "byd", (("Qin Plus", "qin-plus"), ("Seal", "seal"), ("Song Plus", "song-plus"))),
    (
        "Chevrolet",
        "chevrolet",
        (("Cobalt", "cobalt"), ("Malibu", "malibu"), ("Tracker", "tracker")),
    ),
    (
        "Ford",
        "ford",
        (("Escape", "escape"), ("Explorer", "explorer"), ("Fusion", "fusion")),
    ),
    (
        "Honda",
        "honda",
        (("Accord", "accord"), ("Civic", "civic"), ("CR-V", "cr-v"), ("Fit", "fit")),
    ),
    (
        "Hyundai",
        "hyundai",
        (
            ("Avante", "avante"),
            ("Santa Fe", "santa-fe"),
            ("Sonata", "sonata"),
            ("Tucson", "tucson"),
        ),
    ),
    (
        "Kia",
        "kia",
        (("K5", "k5"), ("K7", "k7"), ("Sorento", "sorento"), ("Sportage", "sportage")),
    ),
    ("Lexus", "lexus", (("ES", "es"), ("GX", "gx"), ("LX", "lx"), ("RX", "rx"))),
    (
        "Mazda",
        "mazda",
        (("3", "3"), ("6", "6"), ("CX-5", "cx-5"), ("CX-9", "cx-9")),
    ),
    (
        "Mercedes-Benz",
        "mercedes-benz",
        (
            ("C-Class", "c-class"),
            ("E-Class", "e-class"),
            ("S-Class", "s-class"),
            ("GLC", "glc"),
            ("GLE", "gle"),
        ),
    ),
    (
        "Mitsubishi",
        "mitsubishi",
        (
            ("ASX", "asx"),
            ("Lancer", "lancer"),
            ("Outlander", "outlander"),
            ("Pajero", "pajero"),
        ),
    ),
    (
        "Nissan",
        "nissan",
        (
            ("Altima", "altima"),
            ("Note", "note"),
            ("Teana", "teana"),
            ("X-Trail", "x-trail"),
        ),
    ),
    (
        "Porsche",
        "porsche",
        (("Cayenne", "cayenne"), ("Macan", "macan"), ("Panamera", "panamera")),
    ),
    (
        "Subaru",
        "subaru",
        (
            ("Forester", "forester"),
            ("Legacy", "legacy"),
            ("Outback", "outback"),
            ("XV", "xv"),
        ),
    ),
    (
        "Toyota",
        "toyota",
        (
            ("Avalon", "avalon"),
            ("Camry", "camry"),
            ("Corolla", "corolla"),
            ("Highlander", "highlander"),
            ("Land Cruiser", "land-cruiser"),
            ("Prius", "prius"),
            ("RAV4", "rav4"),
        ),
    ),
    (
        "Volkswagen",
        "volkswagen",
        (("Golf", "golf"), ("Jetta", "jetta"), ("Passat", "passat"), ("Tiguan", "tiguan")),
    ),
    (
        "Volvo",
        "volvo",
        (("S60", "s60"), ("XC60", "xc60"), ("XC90", "xc90")),
    ),
)


def seed_vehicle_catalog(apps, schema_editor):
    database = schema_editor.connection.alias
    Brand = apps.get_model("cars", "Brand")
    Model = apps.get_model("cars", "Model")

    for brand_name, brand_slug, models in VEHICLE_CATALOG:
        brand, _ = Brand.objects.using(database).get_or_create(
            name=brand_name,
            defaults={"slug": brand_slug},
        )
        for model_name, model_slug in models:
            Model.objects.using(database).get_or_create(
                brand=brand,
                name=model_name,
                defaults={"slug": model_slug},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("cars", "0007_alter_carimage_image"),
    ]

    operations = [
        migrations.RunPython(seed_vehicle_catalog, migrations.RunPython.noop),
    ]
