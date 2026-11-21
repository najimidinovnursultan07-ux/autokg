"""
Загрузка объявлений из Excel (.xlsx). Доступна на тарифах с has_excel_import.

Файл сначала проверяется целиком: если хоть одна строка с ошибкой — ничего не
создаётся, салон получает список ошибок с номерами строк. Фото в Excel не
загружаются — их добавляют в кабинете после импорта.
"""
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from apps.cars.models import (
    Car,
    CarBodyType,
    CarCondition,
    CarCurrency,
    CarDriveType,
    CarEngineType,
    CarTransmission,
    City,
    Model,
)
from apps.cars.serializers import CarSerializer

MAX_ROWS = 300
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ERRORS = 50

# (поле, заголовок, обязательное, справочник choices или None)
COLUMNS = [
    ("brand", "Марка", True, None),
    ("model", "Модель", True, None),
    ("year", "Год", True, None),
    ("price", "Цена", True, None),
    ("currency", "Валюта", False, CarCurrency),
    ("mileage", "Пробег, км", False, None),
    ("engine_volume", "Объём двигателя, л", False, None),
    ("engine_type", "Топливо", True, CarEngineType),
    ("transmission", "КПП", True, CarTransmission),
    ("drive_type", "Привод", True, CarDriveType),
    ("body_type", "Кузов", True, CarBodyType),
    ("condition", "Состояние", True, CarCondition),
    ("color", "Цвет", False, None),
    ("city", "Город", True, None),
    ("contact_phone", "Телефон", False, None),
    ("description", "Описание", True, None),
]
LABELS = {field: title for field, title, _, _ in COLUMNS}
LABELS.update({"non_field_errors": "Строка", "status": "Статус"})

EXAMPLE_ROW = [
    "Toyota", "Camry", 2019, 1850000, "сом", 85000, 2.5, "Бензин", "Автоматическая",
    "Передний", "Седан", "С пробегом", "белый", "Бишкек", "", "Один владелец, полное ТО у дилера.",
]


class ImportFileError(Exception):
    """Файл целиком не читается (формат, размер, заголовки)."""


def _norm(value):
    return " ".join(str(value).split()).lower() if value is not None else ""


def _choice_lookup(choices):
    lookup = {}
    for value, label in choices.choices:
        lookup[_norm(value)] = value
        lookup[_norm(label)] = value
    if choices is CarCurrency:
        lookup.update({"сом": "KGS", "kgs": "KGS", "$": "USD", "usd": "USD", "доллар": "USD"})
    return lookup


def _number(value, *, integer=False):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        number = Decimal(str(value))
    else:
        cleaned = str(value).replace("\xa0", "").replace(" ", "").replace(",", ".")
        cleaned = cleaned.lower().removesuffix("км").removesuffix("л")
        try:
            number = Decimal(cleaned)
        except InvalidOperation:
            return str(value)  # пусть сериализатор вернёт понятную ошибку
    return int(number) if integer else str(number)


def build_template():
    wb = Workbook()
    ws = wb.active
    ws.title = "Объявления"
    ref = wb.create_sheet("Справочник")

    header_fill = PatternFill("solid", fgColor="E8F1FD")
    for col, (_, title, required, _) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col, value=f"{title} *" if required else title)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        ws.column_dimensions[get_column_letter(col)].width = max(14, len(title) + 4)
    ws.column_dimensions[get_column_letter(len(COLUMNS))].width = 50
    for col, value in enumerate(EXAMPLE_ROW, start=1):
        ws.cell(row=2, column=col, value=value)
    ws.freeze_panes = "A2"

    # Справочник: допустимые значения + выпадающие списки на листе «Объявления»
    ref_col = 1
    for col, (field, title, _, choices) in enumerate(COLUMNS, start=1):
        if field == "brand":
            values = sorted({m.brand.name for m in Model.objects.filter(is_active=True, brand__is_active=True).select_related("brand")})
        elif field == "city":
            values = list(City.objects.filter(is_active=True).values_list("name", flat=True))
        elif choices is not None:
            values = [label for _, label in choices.choices]
        else:
            continue
        ref.cell(row=1, column=ref_col, value=title).font = Font(bold=True)
        for i, value in enumerate(values, start=2):
            ref.cell(row=i, column=ref_col, value=value)
        letter = get_column_letter(ref_col)
        if values:
            dv = DataValidation(
                type="list",
                formula1=f"'Справочник'!${letter}$2:${letter}${len(values) + 1}",
                allow_blank=True,
                showErrorMessage=False,  # подсказка, а не запрет: проверим на сервере
            )
            ws.add_data_validation(dv)
            dv.add(f"{get_column_letter(col)}2:{get_column_letter(col)}{MAX_ROWS + 1}")
        ref.column_dimensions[letter].width = 22
        ref_col += 1

    # Модели по маркам — отдельной таблицей
    ref.cell(row=1, column=ref_col + 1, value="Марка").font = Font(bold=True)
    ref.cell(row=1, column=ref_col + 2, value="Модели").font = Font(bold=True)
    models = Model.objects.filter(is_active=True, brand__is_active=True).select_related("brand").order_by("brand__name", "name")
    row = 2
    by_brand = {}
    for m in models:
        by_brand.setdefault(m.brand.name, []).append(m.name)
    for brand, names in by_brand.items():
        ref.cell(row=row, column=ref_col + 1, value=brand)
        ref.cell(row=row, column=ref_col + 2, value=", ".join(names))
        row += 1
    ref.column_dimensions[get_column_letter(ref_col + 2)].width = 80

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _read_rows(upload):
    if upload.size > MAX_FILE_BYTES:
        raise ImportFileError("Файл больше 5 МБ.")
    if not upload.name.lower().endswith(".xlsx"):
        raise ImportFileError("Нужен файл Excel в формате .xlsx — скачайте шаблон.")
    try:
        wb = load_workbook(upload, read_only=True, data_only=True)
    except Exception:
        raise ImportFileError("Не удалось прочитать файл. Сохраните его в Excel как .xlsx.")
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None) or ()
    titles = {_norm(str(h).rstrip(" *")): i for i, h in enumerate(header) if h is not None}
    index = {}
    missing = []
    for field, title, required, _ in COLUMNS:
        if _norm(title) in titles:
            index[field] = titles[_norm(title)]
        elif required:
            missing.append(title)
    if missing:
        raise ImportFileError(f"В первой строке нет столбцов: {', '.join(missing)}. Используйте шаблон.")

    result = []
    for number, row in enumerate(rows, start=2):
        values = {f: (row[i] if i < len(row) else None) for f, i in index.items()}
        if all(v is None or str(v).strip() == "" for v in values.values()):
            continue
        result.append((number, values))
        if len(result) > MAX_ROWS:
            raise ImportFileError(f"За один раз можно загрузить не более {MAX_ROWS} объявлений.")
    wb.close()
    if not result:
        raise ImportFileError("В файле нет объявлений — заполните строки под заголовком.")
    return result


def _payload(values, models, cities, lookups):
    errors = {}
    data = {}
    brand, model_name = _norm(values.get("brand")), _norm(values.get("model"))
    model = models.get((brand, model_name))
    if model is None:
        if not brand or not model_name:
            errors["model"] = ["Укажите марку и модель."]
        elif not any(b == brand for b, _ in models):
            errors["brand"] = [f"Марки «{values.get('brand')}» нет в справочнике."]
        else:
            errors["model"] = [f"Модели «{values.get('model')}» нет у этой марки."]
    else:
        data["model"] = model.pk

    city = cities.get(_norm(values.get("city")))
    if city is None:
        errors["city"] = [f"Города «{values.get('city') or ''}» нет в справочнике."]
    else:
        data["city"] = city.pk

    for field, _, required, choices in COLUMNS:
        if choices is None or field not in values:
            continue
        raw = values.get(field)
        if raw is None or str(raw).strip() == "":
            if field == "currency":
                data[field] = "KGS"
            continue
        value = lookups[field].get(_norm(raw))
        if value is None:
            errors[field] = [f"Недопустимое значение «{raw}». Выберите из списка в шаблоне."]
        else:
            data[field] = value

    data["year"] = _number(values.get("year"), integer=True)
    data["price"] = _number(values.get("price"))
    data["mileage"] = _number(values.get("mileage"), integer=True) or 0
    volume = _number(values.get("engine_volume"))
    if volume not in (None, "0"):
        data["engine_volume"] = volume
    for field in ("color", "description"):
        if values.get(field) is not None:
            data[field] = str(values[field]).strip()
    phone = values.get("contact_phone")
    if phone not in (None, ""):
        data["contact_phone"] = str(int(phone)) if isinstance(phone, float) else str(phone).strip()
        if data["contact_phone"].startswith("996"):
            data["contact_phone"] = "+" + data["contact_phone"]
    return {k: v for k, v in data.items() if v is not None}, errors


def _format_errors(number, errors):
    messages = []
    for field, items in errors.items():
        if isinstance(items, dict):
            items = [str(v) for v in items.values()]
        for message in items if isinstance(items, (list, tuple)) else [items]:
            messages.append(f"Строка {number}, «{LABELS.get(field, field)}»: {message}")
    return messages


def import_cars(upload, *, user, dealer, publish):
    """
    Возвращает (result, errors). При ошибках ничего не создаётся.
    publish=True — публикует, пока позволяет лимит тарифа, остальные сохраняет скрытыми.
    """
    from apps.subscriptions.services import current_subscription

    rows = _read_rows(upload)
    models = {
        (_norm(m.brand.name), _norm(m.name)): m
        for m in Model.objects.filter(is_active=True, brand__is_active=True).select_related("brand")
    }
    cities = {_norm(c.name): c for c in City.objects.filter(is_active=True)}
    lookups = {f: _choice_lookup(ch) for f, _, _, ch in COLUMNS if ch is not None}

    serializers, errors = [], []
    for number, values in rows:
        data, row_errors = _payload(values, models, cities, lookups)
        serializer = CarSerializer(data=data)
        if not serializer.is_valid():
            for field, items in serializer.errors.items():
                row_errors.setdefault(field, items)
        if not data.get("contact_phone") and not (dealer.phone or dealer.whatsapp):
            row_errors.setdefault("contact_phone", ["Укажите телефон или заполните телефон в профиле салона."])
        if row_errors:
            errors.extend(_format_errors(number, row_errors))
            if len(errors) >= MAX_ERRORS:
                break
        else:
            serializers.append(serializer)
    if errors:
        return None, errors[:MAX_ERRORS]

    from apps.dealers.models import Dealer

    with transaction.atomic():
        Dealer.objects.select_for_update().get(pk=dealer.pk)
        slots = 0
        if publish:
            subscription = current_subscription(dealer)
            if subscription:
                active = Car.objects.filter(dealer=dealer, status=Car.Status.ACTIVE).count()
                slots = max(subscription.plan.max_active_cars - active, 0)
        now = timezone.now()
        published = 0
        for serializer in serializers:
            make_active = published < slots
            serializer.save(
                owner=user,
                dealer=dealer,
                status=Car.Status.ACTIVE if make_active else Car.Status.HIDDEN,
                published_at=now if make_active else None,
            )
            published += int(make_active)
    created = len(serializers)
    return {"created": created, "published": published, "hidden": created - published}, []
