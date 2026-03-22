"""
report.py — Branded PDF generation with ReportLab.

Produces a professionally styled PDF with:
- Navy header banner
- Per-asset-class sections with direction badges and conviction circles
- Key risks in a shaded box
- Overall macro summary
- Footer with generation date
"""

import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ── Register Unicode-capable fonts (Arial from Windows) ──────────────────────
_FONTS_DIR = "C:/Windows/Fonts"
pdfmetrics.registerFont(TTFont("Arial", f"{_FONTS_DIR}/arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", f"{_FONTS_DIR}/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Italic", f"{_FONTS_DIR}/ariali.ttf"))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", f"{_FONTS_DIR}/arialbi.ttf"))
pdfmetrics.registerFontFamily(
    "Arial",
    normal="Arial",
    bold="Arial-Bold",
    italic="Arial-Italic",
    boldItalic="Arial-BoldItalic",
)

# ── Brand colours ────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#1B2A4A")
NAVY_LIGHT = colors.HexColor("#2C4070")
GOLD = colors.HexColor("#C9A84C")
BULLISH_COLOR = colors.HexColor("#1A7A4A")   # dark green
BEARISH_COLOR = colors.HexColor("#B22222")   # dark red
NEUTRAL_COLOR = colors.HexColor("#5A6475")   # slate grey
RISK_BG = colors.HexColor("#F4F6F9")
SECTION_BG = colors.HexColor("#EEF1F7")
WHITE = colors.white
BLACK = colors.HexColor("#1A1A1A")
LIGHT_GREY = colors.HexColor("#CCCCCC")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


# ── Styles ───────────────────────────────────────────────────────────────────

def _make_styles():
    base = getSampleStyleSheet()

    styles = {
        "report_title": ParagraphStyle(
            "report_title",
            fontName="Arial-Bold",
            fontSize=22,
            textColor=WHITE,
            leading=28,
            spaceAfter=4,
        ),
        "report_subtitle": ParagraphStyle(
            "report_subtitle",
            fontName="Arial",
            fontSize=12,
            textColor=colors.HexColor("#BDC8DC"),
            leading=16,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Arial-Bold",
            fontSize=13,
            textColor=WHITE,
            leading=18,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Arial",
            fontSize=9.5,
            textColor=BLACK,
            leading=14,
            spaceAfter=6,
        ),
        "risk_item": ParagraphStyle(
            "risk_item",
            fontName="Arial",
            fontSize=9,
            textColor=colors.HexColor("#333333"),
            leading=13,
            leftIndent=10,
            spaceAfter=2,
        ),
        "risk_header": ParagraphStyle(
            "risk_header",
            fontName="Arial-Bold",
            fontSize=9,
            textColor=colors.HexColor("#555555"),
            leading=13,
            spaceAfter=3,
        ),
        "overall_header": ParagraphStyle(
            "overall_header",
            fontName="Arial-Bold",
            fontSize=12,
            textColor=NAVY,
            leading=16,
            spaceAfter=6,
        ),
        "overall_body": ParagraphStyle(
            "overall_body",
            fontName="Arial-Italic",
            fontSize=9.5,
            textColor=BLACK,
            leading=14,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Arial",
            fontSize=7.5,
            textColor=colors.HexColor("#888888"),
            leading=10,
            alignment=TA_CENTER,
        ),
        "direction_label": ParagraphStyle(
            "direction_label",
            fontName="Arial-Bold",
            fontSize=9,
            textColor=WHITE,
            leading=12,
            alignment=TA_CENTER,
        ),
        "conviction_label": ParagraphStyle(
            "conviction_label",
            fontName="Arial",
            fontSize=8.5,
            textColor=colors.HexColor("#444444"),
            leading=12,
        ),
    }
    return styles


# ── Helpers ──────────────────────────────────────────────────────────────────

def _direction_color(direction: str) -> colors.Color:
    d = direction.lower()
    if "bull" in d:
        return BULLISH_COLOR
    if "bear" in d:
        return BEARISH_COLOR
    return NEUTRAL_COLOR


def _conviction_circles(score: int) -> str:
    """Return filled/empty circles string for conviction score 1-5."""
    score = max(1, min(5, int(score)))
    filled = "\u25cf" * score
    empty = "\u25cb" * (5 - score)
    return filled + empty


def _section_header_table(asset_name: str, direction: str, conviction: int, styles: dict):
    """Build a two-row table: navy header bar + badges row."""
    dir_color = _direction_color(direction)
    circles = _conviction_circles(conviction)

    # Row 1: asset class name
    header_para = Paragraph(asset_name.upper(), styles["section_header"])
    header_row = [[header_para]]

    header_table = Table(header_row, colWidths=[PAGE_W - 2 * MARGIN])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    # Row 2: direction badge + conviction
    dir_para = Paragraph(f" {direction.upper()} ", styles["direction_label"])
    conv_text = f"Conviction: {circles}  ({conviction}/5)"
    conv_para = Paragraph(conv_text, styles["conviction_label"])

    badge_table = Table(
        [[dir_para, conv_para]],
        colWidths=[90, PAGE_W - 2 * MARGIN - 90],
    )
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), dir_color),
        ("BACKGROUND", (1, 0), (1, 0), SECTION_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    return [header_table, badge_table]


def _risks_box(risks: list[str], styles: dict):
    """Build a light-grey box containing key risks."""
    items = [Paragraph("KEY RISKS", styles["risk_header"])]
    for risk in risks:
        items.append(Paragraph(f"\u2022  {risk}", styles["risk_item"]))

    inner = Table([[item] for item in items], colWidths=[PAGE_W - 2 * MARGIN - 20])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RISK_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (0, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 2),
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, GOLD),
    ]))
    return inner


# ── Page template with header/footer ─────────────────────────────────────────

class _BrandedDoc(BaseDocTemplate):
    def __init__(self, filename: str, report_month: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.report_month = report_month
        self._gen_date = datetime.now().strftime("%d %B %Y")

        frame = Frame(
            MARGIN, MARGIN + 1 * cm,        # x, y (leave room for footer)
            PAGE_W - 2 * MARGIN,
            PAGE_H - 2 * MARGIN - 1 * cm,  # height
            id="main",
        )
        template = PageTemplate(id="main", frames=[frame], onPage=self._draw_page)
        self.addPageTemplates([template])

    def _draw_page(self, canvas, doc):
        canvas.saveState()

        # ── header banner ──────────────────────────────────────────────────
        banner_h = 70
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - banner_h, PAGE_W, banner_h, fill=1, stroke=0)

        # gold accent line below banner
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(2)
        canvas.line(0, PAGE_H - banner_h, PAGE_W, PAGE_H - banner_h)

        # title text
        canvas.setFillColor(WHITE)
        canvas.setFont("Arial-Bold", 18)
        canvas.drawString(MARGIN, PAGE_H - 30, "Monthly Investment Outlook")

        canvas.setFillColor(colors.HexColor("#BDC8DC"))
        canvas.setFont("Arial", 11)
        canvas.drawString(MARGIN, PAGE_H - 50, self.report_month)

        # page number (top-right)
        canvas.setFont("Arial", 9)
        canvas.setFillColor(colors.HexColor("#BDC8DC"))
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 40, f"Page {doc.page}")

        # ── footer ─────────────────────────────────────────────────────────
        canvas.setStrokeColor(LIGHT_GREY)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, MARGIN + 12, PAGE_W - MARGIN, MARGIN + 12)

        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.setFont("Arial", 7)
        canvas.drawString(MARGIN, MARGIN + 4,
                          f"Generated {self._gen_date}  |  For informational purposes only. "
                          "Not financial advice.")
        canvas.drawRightString(PAGE_W - MARGIN, MARGIN + 4,
                               "AI-generated research synthesis")

        canvas.restoreState()


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_pdf(data: dict, output_dir: str = "output") -> str:
    """
    Generate a branded PDF from structured data.

    Args:
        data: Dict from agent.synthesize() — see agent.py for schema.
        output_dir: Directory to save the PDF.

    Returns:
        Absolute path of the saved PDF file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    report_month = data.get("report_month", datetime.now().strftime("%B %Y"))
    month_tag = datetime.now().strftime("%Y%m")
    filename = os.path.join(output_dir, f"monthly_outlook_{month_tag}.pdf")

    styles = _make_styles()
    doc = _BrandedDoc(
        filename,
        report_month=report_month,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN + 70,  # leave room for header banner
        bottomMargin=MARGIN + 1 * cm,
    )

    story = []

    # ── Asset class sections ───────────────────────────────────────────────
    for ac in data.get("asset_classes", []):
        name = ac.get("name", "Asset Class")
        macro = ac.get("macro_summary", "")
        direction = ac.get("direction", "Neutral")
        conviction = ac.get("conviction", 3)
        risks = ac.get("risks", [])

        # Section header + badge
        story += _section_header_table(name, direction, conviction, styles)
        story.append(Spacer(1, 6))

        # Macro summary
        story.append(Paragraph(macro, styles["body"]))
        story.append(Spacer(1, 4))

        # Key risks box
        if risks:
            story.append(_risks_box(risks, styles))

        story.append(Spacer(1, 14))

    # ── Overall macro summary ──────────────────────────────────────────────
    overall = data.get("overall_macro_summary", "")
    if overall:
        story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=10))
        story.append(Paragraph("Overall Macro Summary", styles["overall_header"]))

        summary_table = Table(
            [[Paragraph(overall, styles["overall_body"])]],
            colWidths=[PAGE_W - 2 * MARGIN],
        )
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SECTION_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LINEBEFORE", (0, 0), (0, -1), 3, NAVY),
        ]))
        story.append(summary_table)

    doc.build(story)
    return os.path.abspath(filename)
