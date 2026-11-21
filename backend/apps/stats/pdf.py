"""PDF-отчёт салона за месяц (A4 книжная)."""
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.admin_api.report_pdf import FONT, FONT_BOLD, HEAD, INK, LINE, MUTED, SOFT, _register_fonts

STATUS_LABELS = {"active": "на сайте", "hidden": "скрыто", "sold": "продано", "deleted": "удалено"}


def _num(value):
    return "—" if value is None else f"{int(value):,}".replace(",", " ")


def _price(value, currency):
    if value is None:
        return "—"
    amount = f"{int(Decimal(value)):,}".replace(",", " ")
    return f"${amount}" if currency == "USD" else f"{amount} сом"


def _delta(current, previous):
    if current is None or previous is None:
        return ""
    diff = current - previous
    return "" if diff == 0 else (f"+{_num(diff)}" if diff > 0 else f"−{_num(-diff)}")


def build_dealer_report_pdf(report):
    _register_fonts()
    st = {
        "title": ParagraphStyle("t", fontName=FONT_BOLD, fontSize=16, leading=20, textColor=INK),
        "sub": ParagraphStyle("s", fontName=FONT, fontSize=8.5, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h", fontName=FONT_BOLD, fontSize=11, leading=14, textColor=INK, spaceBefore=10, spaceAfter=5),
        "cell": ParagraphStyle("c", fontName=FONT, fontSize=8, leading=10, textColor=INK),
        "note": ParagraphStyle("n", fontName=FONT, fontSize=7, leading=9, textColor=MUTED, spaceBefore=6),
    }
    base = [
        ("FONTNAME", (0, 0), (-1, -1), FONT), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    cur, prev = report["current"], report["previous"]
    plan = report["plan"]
    plan_text = (
        f"{plan['name']}{' (пробный)' if plan['is_trial'] else ''}, до {timezone.localtime(plan['expires_at']):%d.%m.%Y}"
        if plan["name"] else "не активен"
    )
    story = [
        Paragraph(f"Отчёт салона «{escape(report['dealer']['name'])}»", st["title"]),
        Paragraph(
            f"{report['month_label']}{' (месяц ещё идёт)' if report['is_current_month'] else ''} · "
            f"тариф: {escape(plan_text)} · сформирован {timezone.localtime():%d.%m.%Y %H:%M}",
            st["sub"],
        ),
        Spacer(1, 5 * mm),
        Paragraph("Итоги месяца", st["h2"]),
    ]
    rows = [["Показатель", "За месяц", "Прошлый месяц", "Изменение"]]
    for label, key in [
        ("Продано автомобилей", "cars_sold"), ("Добавлено объявлений", "cars_added"),
        ("Просмотры объявлений", "views"), ("Открыли номер", "phone_views"), ("Нажали WhatsApp", "whatsapp_clicks"),
    ]:
        rows.append([label, _num(cur[key]), _num(prev[key]), _delta(cur[key], prev[key])])
    rate = cur["contact_rate"]
    rows.append(["Конверсия в контакт", "—" if rate is None else f"{rate}%",
                 "—" if prev["contact_rate"] is None else f"{prev['contact_rate']}%", ""])
    promo = report["promotions"]
    rows.append(["Продвижения (ТОП / выделение / срочно)", f"{promo['top']} / {promo['highlight']} / {promo['urgent']}", "", ""])
    summary = Table(rows, colWidths=[78 * mm, 32 * mm, 32 * mm, 28 * mm], hAlign="LEFT")
    summary.setStyle(TableStyle(base + [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", SOFT]), ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(summary)

    lst = report["listings"]
    story.append(Paragraph("Объявления сейчас", st["h2"]))
    now_rows = [
        ["Всего", "На сайте / лимит", "Срок истёк", "Скрыто", "Продано (всего)"],
        [_num(lst["total"]), f"{_num(lst['on_site'])} / {_num(lst['limit'])}", _num(lst["expired"]),
         _num(lst["hidden"]), _num(lst["sold"])],
    ]
    now_table = Table(now_rows, colWidths=[34 * mm] * 5, hAlign="LEFT")
    now_table.setStyle(TableStyle(base + [
        ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 1), (-1, 1), FONT_BOLD),
        ("FONTSIZE", (0, 1), (-1, 1), 11), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(now_table)

    story.append(Paragraph(f"Продано за месяц: {len(report['sold'])}", st["h2"]))
    if report["sold"]:
        sold_rows = [["Автомобиль", "Цена", "Дата продажи", "Дней на сайте"]]
        for car in report["sold"]:
            sold_rows.append([
                Paragraph(escape(car["title"]), st["cell"]), _price(car["price"], car["currency"]),
                timezone.localtime(car["sold_at"]).strftime("%d.%m.%Y"), _num(car["days_on_site"]),
            ])
        sold_table = Table(sold_rows, colWidths=[76 * mm, 36 * mm, 32 * mm, 36 * mm], repeatRows=1, hAlign="LEFT")
        sold_table.setStyle(TableStyle(base + [
            ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", SOFT]), ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(sold_table)
    else:
        story.append(Paragraph("В этом месяце продаж не отмечено.", st["sub"]))

    story.append(Paragraph("Объявления по просмотрам за месяц", st["h2"]))
    if report["top_cars"]:
        top_rows = [["Автомобиль", "Статус", "Цена", "Просмотры", "Номер", "WhatsApp"]]
        for car in report["top_cars"]:
            top_rows.append([
                Paragraph(escape(car["title"]), st["cell"]), STATUS_LABELS.get(car["status"], car["status"]),
                _price(car["price"], car["currency"]), _num(car["views"]),
                _num(car["phone_views"]), _num(car["whatsapp_clicks"]),
            ])
        top_table = Table(top_rows, colWidths=[60 * mm, 20 * mm, 30 * mm, 24 * mm, 20 * mm, 26 * mm], repeatRows=1, hAlign="LEFT")
        top_table.setStyle(TableStyle(base + [
            ("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["white", SOFT]), ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(top_table)
    else:
        story.append(Paragraph("Просмотров в этом месяце пока нет.", st["sub"]))

    notes = [
        f"Данные за каждый месяц хранятся {report['retention_months']} месяцев, затем удаляются. "
        f"Данные за {report['month_label'].lower()} будут удалены {report['deleted_after']:%d.%m.%Y}.",
    ]
    if not report["show_contacts"]:
        notes.append("Открытия номера и WhatsApp доступны на тарифах «Бизнес» и «Премиум».")
    story += [Paragraph(" ".join(notes), st["note"])]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(doc.leftMargin, 8 * mm, f"AutoBuy — {report['dealer']['name']} — {report['month_label']}")
        canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 8 * mm, f"стр. {doc.page}")
        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Отчёт {report['dealer']['name']} — {report['month_label']}", author="AutoBuy",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
