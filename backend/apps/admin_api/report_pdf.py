"""PDF-версия отчёта по автосалонам (A4 альбомная). Шрифт DejaVu Sans — для кириллицы."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT, FONT_BOLD = "DejaVuSans", "DejaVuSans-Bold"

INK = colors.HexColor("#172b4d")
MUTED = colors.HexColor("#718096")
LINE = colors.HexColor("#e3eaf3")
HEAD = colors.HexColor("#e8f1fd")
SOFT = colors.HexColor("#f5f8fc")
WARN = colors.HexColor("#b7791f")


def _register_fonts():
    if FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT, str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD)


def _num(value):
    return f"{int(value or 0):,}".replace(",", " ")


def _money(value):
    amount = Decimal(value or 0)
    return f"{_num(amount)} сом" if amount else "—"


def _date(value):
    return timezone.localtime(value).strftime("%d.%m.%Y") if value else ""


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 8 * mm, "AutoBuy — отчёт по автосалонам")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 8 * mm, f"стр. {doc.page}")
    canvas.restoreState()


def build_report_pdf(report, start, end):
    _register_fonts()
    styles = {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=16, leading=20, textColor=INK),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=8.5, leading=12, textColor=MUTED),
        "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=5),
        "cell": ParagraphStyle("cell", fontName=FONT, fontSize=7, leading=8.6, textColor=INK),
        "cell_bold": ParagraphStyle("cell_bold", fontName=FONT_BOLD, fontSize=7, leading=8.6, textColor=INK),
        "small": ParagraphStyle("small", fontName=FONT, fontSize=6.3, leading=7.6, textColor=MUTED),
        "note": ParagraphStyle("note", fontName=FONT, fontSize=7, leading=9, textColor=MUTED, spaceBefore=6),
    }
    s = report["summary"]
    story = [
        Paragraph("Отчёт по автосалонам AutoBuy", styles["title"]),
        Paragraph(
            f"Период: {start:%d.%m.%Y} — {end:%d.%m.%Y} · сформирован {timezone.localtime():%d.%m.%Y %H:%M}",
            styles["sub"],
        ),
        Spacer(1, 6 * mm),
    ]

    # ── Итоги: 4 колонки «показатель — значение» ──
    kpis = [
        ("Оплачено за период", _money(s["revenue"])), ("Оплат", _num(s["payments"])),
        ("Автосалонов", _num(s["dealers"])), ("На платном тарифе", _num(s["dealers_paid"])),
        ("На пробном периоде", _num(s["dealers_trial"])), ("Без тарифа", _num(s["dealers_without_plan"])),
        ("Тариф кончается ≤ 7 дн.", _num(s["expiring_soon"])), ("Новых заявок", _num(s["new_requests"])),
        ("Объявлений на сайте", _num(s["cars_on_site"])), ("Добавлено за период", _num(s["cars_added"])),
        ("Срок истёк", _num(s["cars_expired"])), ("Продано", _num(s["cars_sold"])),
        ("Просмотров*", _num(s["views"])), ("Открыли номер*", _num(s["phone_views"])),
        ("WhatsApp*", _num(s["whatsapp_clicks"])), ("Продвижений за период", _num(s["promotions"])),
    ]
    grid = []
    for i in range(0, len(kpis), 4):
        row = []
        for label, value in kpis[i:i + 4]:
            row += [Paragraph(label, styles["small"]), Paragraph(f"<b>{value}</b>", styles["cell"])]
        grid.append(row)
    kpi_table = Table(grid, colWidths=[38 * mm, 27 * mm] * 4, hAlign="LEFT")
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [kpi_table, Spacer(1, 3 * mm)]
    plans = " · ".join(f"{escape(label)}: {count}" for label, count in report["plans"].items()) or "—"
    story.append(Paragraph(f"<b>Салоны по тарифам:</b> {plans}", styles["cell"]))

    # ── Таблица по салонам ──
    story.append(Paragraph("По автосалонам", styles["h2"]))
    header = [
        "Салон", "Тариф", "На сайте / лимит", "Срок истёк", "Скры-<br/>то", "Про-<br/>дано", "Добав-<br/>лено",
        "Просмот-<br/>ры*", "Номер*", "What-<br/>sApp*", "Конвер-<br/>сия", "ТОП / выд. / срочно", "Оплачено", "Рейтинг",
        "Заяв-<br/>ки",
    ]
    data = [[Paragraph(f"<b>{h}</b>", styles["cell"]) for h in header]]
    warn_rows = []
    rows = sorted(report["rows"], key=lambda r: (-Decimal(r["revenue"]), r["name"].lower()))
    for r in rows:
        name = f"<b>{escape(r['name'])}</b>"
        meta = escape(" · ".join(filter(None, [r["city"], r["phone"]])))
        if not r["is_active"]:
            meta = f"{meta} · отключён" if meta else "отключён"
        if r["plan"]:
            plan = (
                f"{r['plan']}{' (проб.)' if r['is_trial'] else ''} · {r['days_left']} дн."
                f"<br/><font size=6 color='#718096'>до {_date(r['expires_at'])}</font>"
            )
            if r["days_left"] is not None and r["days_left"] <= 7:
                warn_rows.append(len(data))
        else:
            plan = "<b>нет тарифа</b>"
        data.append([
            Paragraph(f"{name}<br/><font size=6 color='#718096'>{meta}</font>", styles["cell"]),
            Paragraph(plan, styles["cell"]),
            f"{r['cars_on_site']} / {r['max_cars']}" if r["max_cars"] else str(r["cars_on_site"]),
            _num(r["cars_expired"]), _num(r["cars_hidden"]), _num(r["cars_sold"]), _num(r["cars_added"]),
            _num(r["views"]), _num(r["phone_views"]), _num(r["whatsapp_clicks"]),
            "—" if r["contact_rate"] is None else f"{r['contact_rate']}%",
            f"{r['promo_top']} / {r['promo_highlight']} / {r['promo_urgent']}",
            _money(r["revenue"]),
            f"★ {r['rating']:.1f} ({r['reviews']})" if r["rating"] else "—",
            _num(r["new_requests"]) if r["new_requests"] else "—",
        ])
    views = s["views"]
    rate = f"{round((s['phone_views'] + s['whatsapp_clicks']) / views * 100, 1)}%" if views else "—"
    promo_totals = [sum(r[k] for r in rows) for k in ("promo_top", "promo_highlight", "promo_urgent")]
    data.append([
        Paragraph(f"<b>Итого ({len(rows)})</b>", styles["cell"]), "",
        _num(s["cars_on_site"]), _num(s["cars_expired"]), _num(s["cars_hidden"]), _num(s["cars_sold"]),
        _num(s["cars_added"]), _num(s["views"]), _num(s["phone_views"]), _num(s["whatsapp_clicks"]), rate,
        " / ".join(str(n) for n in promo_totals), _money(s["revenue"]), "", _num(s["new_requests"]),
    ])

    widths = [39, 32, 17, 13, 13, 13, 13, 17, 14, 16, 15, 20, 21, 18, 11]
    table = Table(data, colWidths=[w * mm for w in widths], repeatRows=1, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("BACKGROUND", (0, 0), (-1, 0), HEAD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, SOFT]),
        ("BACKGROUND", (0, -1), (-1, -1), HEAD),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, LINE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for index in warn_rows:
        style.append(("TEXTCOLOR", (1, index), (1, index), WARN))
    table.setStyle(TableStyle(style))
    story += [
        table,
        Paragraph(
            "* Просмотры, открытия номера и WhatsApp — за всё время (по дням пока не хранятся). "
            "Добавленные объявления, продвижения и оплаты — за выбранный период. "
            "Конверсия — (номер + WhatsApp) / просмотры.",
            styles["note"],
        ),
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=10 * mm, bottomMargin=14 * mm,
        title="Отчёт по автосалонам AutoBuy", author="AutoBuy",
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
