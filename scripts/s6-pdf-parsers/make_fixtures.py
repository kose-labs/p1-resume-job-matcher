"""Generate synthetic CV PDFs for the parser comparison.

Every name, employer and contact detail is fictional, so these files are safe to commit and reuse
as backend test fixtures. `fixtures/truth.json` records the text drawn on each page and what a
correct extractor should report.
"""

import json
from pathlib import Path

import pymupdf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "fixtures"
WIDTH, HEIGHT = A4

HEADER = ["JORDAN EXAMPLE", "Backend Engineer · jordan@example.com · Accra"]
BODY = [
    "SUMMARY",
    "Backend engineer with 4 years of experience building REST APIs in Python and Node.js.",
    "EXPERIENCE",
    "Software Engineer, Example Fintech (2022–2026)",
    "• Built FastAPI services handling 2,000 requests per minute.",
    "• Cut CI time by 40% with caching and parallel test runs.",
    "• Migrated a C# reporting tool to Python and PostgreSQL.",
    "Junior Developer, Sample Labs (2020–2022)",
    "• Maintained C++ data pipelines and wrote unit tests with GoogleTest.",
    "SKILLS",
    "Python, FastAPI, Node.js, C++, C#, Go, PostgreSQL, Docker, GitHub Actions",
    "EDUCATION",
    "BSc Computer Engineering, Example University (2020)",
]

SIDEBAR = [
    "CONTACT",
    "jordan@example.com",
    "Accra, Ghana",
    "SKILLS",
    "Python",
    "FastAPI",
    "Node.js",
    "C++ and C#",
    "PostgreSQL",
    "Docker",
    "LANGUAGES",
    "English",
    "French",
]
MAIN = [
    "JORDAN EXAMPLE",
    "Backend Engineer",
    "SUMMARY",
    "Builds reliable REST APIs in Python and Node.js.",
    "EXPERIENCE",
    "Software Engineer, Example Fintech",
    "2022–2026 · Accra",
    "• Built FastAPI services for card payments.",
    "• Cut CI time by 40% with caching.",
    "• Migrated a C# tool to Python.",
    "Junior Developer, Sample Labs",
    "2020–2022 · Kumasi",
    "• Maintained C++ data pipelines.",
]


def draw_lines(pdf: canvas.Canvas, lines: list[str], x: float, top: float, size: int = 10) -> None:
    """Draw one line of text per entry, top to bottom, starting at (x, top)."""
    y = top
    for line in lines:
        pdf.setFont("Helvetica-Bold" if line.isupper() else "Helvetica", size)
        pdf.drawString(x, y, line)
        y -= size * 1.6


def one_column(path: Path, pages: int = 1, password: str | None = None) -> list[str]:
    """Write a single-column CV, optionally repeated over several pages or encrypted."""
    pdf = canvas.Canvas(str(path), pagesize=A4, encrypt=password)
    for _ in range(pages):
        draw_lines(pdf, HEADER + BODY, 50, HEIGHT - 60)
        pdf.showPage()
    pdf.save()
    return (HEADER + BODY) * pages


def two_column(path: Path, row_order: bool = False) -> None:
    """Write a sidebar + main column CV whose lines share baselines.

    By default each column is stored in the file as one run (column order). With `row_order`,
    lines are stored left, right, left, right across the page, as many word processors and design
    tools write them. Both look identical on screen; only extractors that understand columns get
    the row-ordered one right.
    """
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setFillGray(0.93)
    pdf.rect(0, 0, 190, HEIGHT, stroke=0, fill=1)
    pdf.setFillGray(0)
    if row_order:
        for i in range(max(len(SIDEBAR), len(MAIN))):
            top = HEIGHT - 60 - i * 16
            draw_lines(pdf, SIDEBAR[i : i + 1], 30, top)
            draw_lines(pdf, MAIN[i : i + 1], 220, top)
    else:
        draw_lines(pdf, SIDEBAR, 30, HEIGHT - 60)
        draw_lines(pdf, MAIN, 220, HEIGHT - 60)
    pdf.showPage()
    pdf.save()


def image_only(source: Path, path: Path) -> None:
    """Rasterise `source` and save it as a PDF with no text layer, like a scanned CV."""
    with pymupdf.open(source) as src, pymupdf.open() as out:
        for page in src:
            pixmap = page.get_pixmap(dpi=150)
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, pixmap=pixmap)
        out.save(path)


def main() -> None:
    """Write every fixture and the ground truth file."""
    OUT.mkdir(exist_ok=True)
    truth: dict[str, dict[str, object]] = {}

    truth["one_column.pdf"] = {"expect": "text", "orders": [one_column(OUT / "one_column.pdf")]}
    truth["multi_page.pdf"] = {
        "expect": "text",
        "orders": [one_column(OUT / "multi_page.pdf", pages=3)],
    }
    two_column(OUT / "two_column.pdf")
    # Either column first is a correct reading order; interleaving the two is not.
    truth["two_column.pdf"] = {"expect": "text", "orders": [SIDEBAR + MAIN, MAIN + SIDEBAR]}
    two_column(OUT / "two_column_rows.pdf", row_order=True)
    truth["two_column_rows.pdf"] = {"expect": "text", "orders": [SIDEBAR + MAIN, MAIN + SIDEBAR]}
    image_only(OUT / "one_column.pdf", OUT / "image_only.pdf")
    truth["image_only.pdf"] = {"expect": "no_text", "orders": []}
    one_column(OUT / "encrypted.pdf", password="not-the-password")
    truth["encrypted.pdf"] = {"expect": "unreadable", "orders": []}

    (OUT / "truth.json").write_text(json.dumps(truth, indent=2, ensure_ascii=False), "utf-8")
    print(f"wrote {len(truth)} fixtures to {OUT}")


if __name__ == "__main__":
    main()
