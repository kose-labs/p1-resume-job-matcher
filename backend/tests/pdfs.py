"""Synthetic test PDFs, built in memory when the tests run, so no binary files live in git.

Every name and detail is fictional (a made-up "Jordan Example"), never a real CV.
"""

import io

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

WIDTH, HEIGHT = A4

CV_LINES = [
    "JORDAN EXAMPLE",
    "Backend Engineer",
    "Built FastAPI services in Python with PostgreSQL and Docker.",
    "Maintained C++ data pipelines and wrote unit tests.",
    "Skills: Python, FastAPI, Node.js, C#, Go, PostgreSQL",
]
SIDEBAR = ["CONTACT", "jordan@example.com", "SKILLS", "Python", "Docker", "PostgreSQL"]
MAIN = [
    "JORDAN EXAMPLE",
    "Backend Engineer",
    "Builds reliable REST APIs.",
    "Cut CI time by 40 percent.",
    "Migrated a C# tool to Python.",
    "Maintained C++ pipelines.",
]


def _draw(pdf: canvas.Canvas, lines: list[str], x: float, top: float) -> None:
    for i, line in enumerate(lines):
        pdf.drawString(x, top - i * 16, line)


def text_pdf(pages: int = 1, password: str | None = None, lines: list[str] | None = None) -> bytes:
    """A one-column CV, optionally repeated over several pages, password-protected, or with
    custom lines."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, encrypt=password)
    for _ in range(pages):
        _draw(pdf, lines or CV_LINES, 50, HEIGHT - 60)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def two_column_rows_pdf() -> bytes:
    """A sidebar + main column CV stored row by row, the layout naive extractors interleave."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    for i in range(max(len(SIDEBAR), len(MAIN))):
        top = HEIGHT - 60 - i * 16
        if i < len(SIDEBAR):
            pdf.drawString(30, top, SIDEBAR[i])
        if i < len(MAIN):
            pdf.drawString(220, top, MAIN[i])
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def image_only_pdf() -> bytes:
    """A 'scanned' CV: the text is pixels in an image, with no text layer."""
    image = Image.new("RGB", (800, 300), "white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(CV_LINES):
        draw.text((20, 20 + i * 40), line, fill="black")
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.drawImage(ImageReader(image), 40, HEIGHT - 400, width=520, height=200)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


TEXT_PDF = text_pdf()
