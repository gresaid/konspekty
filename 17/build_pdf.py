from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
)


BASE_DIR = Path(__file__).resolve().parent
MD_PATH = BASE_DIR / "конспект.md"
PDF_PATH = BASE_DIR / "конспект.pdf"
FONTS_DIR = Path(r"C:\Windows\Fonts")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("TimesNewRoman", str(FONTS_DIR / "times.ttf")))
    pdfmetrics.registerFont(TTFont("TimesNewRoman-Bold", str(FONTS_DIR / "timesbd.ttf")))
    pdfmetrics.registerFont(TTFont("TimesNewRoman-Italic", str(FONTS_DIR / "timesi.ttf")))
    pdfmetrics.registerFont(
        TTFont("JetBrainsMono", str(FONTS_DIR / "JetBrainsMono-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("JetBrainsMono-Medium", str(FONTS_DIR / "JetBrainsMono-Medium.ttf"))
    )


def build_styles() -> StyleSheet1:
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ArticleTitle",
            fontName="TimesNewRoman-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ArticleSubtitle",
            fontName="TimesNewRoman",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=18,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1Article",
            fontName="TimesNewRoman-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.black,
            spaceBefore=14,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H2Article",
            fontName="TimesNewRoman-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.black,
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H3Article",
            fontName="TimesNewRoman-Bold",
            fontSize=11.5,
            leading=14,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyArticle",
            fontName="TimesNewRoman",
            fontSize=11.5,
            leading=16,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
            firstLineIndent=7 * mm,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyNoIndent",
            parent=styles["BodyArticle"],
            firstLineIndent=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ListArticle",
            fontName="TimesNewRoman",
            fontSize=11.5,
            leading=15.5,
            alignment=TA_LEFT,
            textColor=colors.black,
            leftIndent=0,
            firstLineIndent=0,
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeArticle",
            fontName="JetBrainsMono",
            fontSize=9,
            leading=12,
            textColor=colors.black,
            leftIndent=5 * mm,
            rightIndent=5 * mm,
            borderColor=colors.black,
            borderWidth=0.6,
            borderPadding=6,
            backColor=colors.white,
            spaceBefore=4,
            spaceAfter=8,
        )
    )

    return styles


def inline_markup(text: str) -> str:
    result: List[str] = []
    i = 0
    while i < len(text):
        if text[i] == "`":
            j = text.find("`", i + 1)
            if j != -1:
                code = escape(text[i + 1 : j])
                result.append(
                    f'<font name="JetBrainsMono">{code}</font>'
                )
                i = j + 1
                continue
        result.append(escape(text[i]))
        i += 1
    return "".join(result)


@dataclass
class ListEntry:
    indent: int
    text: str
    ordered: bool


def parse_list_line(line: str) -> ListEntry | None:
    expanded = line.replace("\t", "    ")
    indent = len(expanded) - len(expanded.lstrip(" "))
    stripped = expanded[indent:]
    if stripped.startswith("- "):
        return ListEntry(indent=indent // 2, text=stripped[2:].strip(), ordered=False)
    if len(stripped) > 3 and stripped[0].isdigit():
        pos = stripped.find(". ")
        if pos != -1 and stripped[:pos].isdigit():
            return ListEntry(indent=indent // 2, text=stripped[pos + 2 :].strip(), ordered=True)
    return None


def render_list(entries: List[ListEntry], styles: StyleSheet1):
    if not entries:
        return []

    grouped: List[List[ListEntry]] = []
    current: List[ListEntry] = [entries[0]]

    for entry in entries[1:]:
        prev = current[-1]
        if entry.ordered == prev.ordered:
            current.append(entry)
        else:
            grouped.append(current)
            current = [entry]
    grouped.append(current)

    flowables = []
    for group in grouped:
        items = []
        for entry in group:
            left = 6 * mm + entry.indent * 8 * mm
            bullet_indent = 4 * mm
            style = ParagraphStyle(
                name=f"ListLevel{entry.indent}_{'o' if entry.ordered else 'u'}",
                parent=styles["ListArticle"],
                leftIndent=left,
                firstLineIndent=0,
            )
            paragraph = Paragraph(inline_markup(entry.text), style)
            item = ListItem(paragraph, leftIndent=left, bulletIndent=left - bullet_indent)
            items.append(item)

        flowables.append(
            ListFlowable(
                items,
                bulletType="1" if group[0].ordered else "bullet",
                start="1",
            )
        )
        flowables.append(Spacer(1, 2))
    return flowables


def add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("TimesNewRoman", 10)
    page_label = f"{canvas.getPageNumber()}"
    width = A4[0]
    canvas.drawCentredString(width / 2, 10 * mm, page_label)
    canvas.restoreState()


def build_story(markdown_text: str, styles: StyleSheet1):
    story = []
    lines = markdown_text.splitlines()

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Конспект по заданию 17", styles["ArticleTitle"]))
    story.append(
        Paragraph(
            "Теория, шаблоны решений и подробный разбор типовых прототипов",
            styles["ArticleSubtitle"],
        )
    )
    story.append(
        HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=10)
    )

    paragraph_buffer: List[str] = []
    list_buffer: List[ListEntry] = []
    code_buffer: List[str] = []
    in_code = False
    seen_first_h1 = False

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if not paragraph_buffer:
            return
        text = " ".join(chunk.strip() for chunk in paragraph_buffer).strip()
        if text:
            story.append(Paragraph(inline_markup(text), styles["BodyArticle"]))
        paragraph_buffer = []

    def flush_list() -> None:
        nonlocal list_buffer
        if not list_buffer:
            return
        story.extend(render_list(list_buffer, styles))
        list_buffer = []

    def flush_code() -> None:
        nonlocal code_buffer
        if not code_buffer:
            return
        story.append(Preformatted("\n".join(code_buffer), styles["CodeArticle"]))
        code_buffer = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_buffer.append(line)
            continue

        list_entry = parse_list_line(line)
        if list_entry is not None:
            flush_paragraph()
            list_buffer.append(list_entry)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            story.append(Spacer(1, 2))
            continue

        if stripped == "---":
            flush_paragraph()
            flush_list()
            story.append(Spacer(1, 6))
            continue

        if stripped.startswith("# "):
            flush_paragraph()
            flush_list()
            text = stripped[2:].strip()
            if seen_first_h1:
                story.append(PageBreak())
            story.append(Paragraph(text, styles["H1Article"]))
            seen_first_h1 = True
            continue

        if stripped.startswith("## "):
            flush_paragraph()
            flush_list()
            story.append(Paragraph(stripped[3:].strip(), styles["H2Article"]))
            continue

        if stripped.startswith("### "):
            flush_paragraph()
            flush_list()
            story.append(Paragraph(stripped[4:].strip(), styles["H3Article"]))
            continue

        flush_list()
        paragraph_buffer.append(stripped)

    flush_paragraph()
    flush_list()
    flush_code()
    return story


def build_pdf() -> Path:
    register_fonts()
    styles = build_styles()
    markdown_text = MD_PATH.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=22 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Конспект по заданию 17",
        author="Codex",
    )

    story = build_story(markdown_text, styles)
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return PDF_PATH


if __name__ == "__main__":
    print(build_pdf())
