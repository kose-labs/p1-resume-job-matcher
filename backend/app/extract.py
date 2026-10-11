"""Turn an uploaded CV PDF into text, as decided in ADR-0003: pdfplumber plus our column split.

Everything happens in memory; the PDF is opened from bytes and never written to disk. Failures
raise `PdfError` with a stable code, which the API turns into a 422 response.
"""

import io
import re
from typing import Any

import pdfplumber
from pdfminer.psexceptions import PSException
from pdfplumber.utils.exceptions import PdfminerException

MAX_PAGES = 10
# Fewer visible characters than this per page, on average, means no usable text layer (ADR-0003).
MIN_CHARS_PER_PAGE = 25


class PdfError(Exception):
    """The PDF can't be used; `code` and `message` go straight into the API's error response."""

    def __init__(self, code: str, message: str) -> None:
        """Store the stable error code and the message shown to the user."""
        super().__init__(message)
        self.code = code
        self.message = message


UNREADABLE = PdfError(
    "pdf_unreadable",
    "We couldn't read this PDF. It may be password-protected or damaged; try exporting it again.",
)
TOO_MANY_PAGES = PdfError("pdf_too_many_pages", f"The CV must be {MAX_PAGES} pages or fewer.")
NO_TEXT = PdfError(
    "pdf_no_text",
    "This PDF has no selectable text, so it looks scanned. "
    "Please upload a PDF exported from Word or Google Docs.",
)


def column_split(words: list[dict[str, Any]], width: float, min_gap: float = 15) -> float | None:
    """Return the x position of the gap between two columns, or None for a one-column page.

    Marks every horizontal point covered by a word, then looks for the widest uncovered strip
    that starts in the middle 60% of the page **and has text on both sides**. One-column pages
    have no such strip because full-width lines cover it, and the empty space after a column of
    short lines doesn't count, because nothing lies to its right.
    """
    covered = [False] * (int(width) + 2)
    for word in words:
        for x in range(max(int(word["x0"]), 0), min(int(word["x1"]), int(width)) + 1):
            covered[x] = True
    band_start, band_end = int(width * 0.2), int(width * 0.8)
    gaps: list[tuple[int, int]] = []
    start: int | None = None
    for x in range(band_start, len(covered)):
        if covered[x] and start is not None:
            gaps.append((start, x))
            start = None
        elif not covered[x] and start is None and x <= band_end:
            start = x
    real = [(s, e) for s, e in gaps if any(covered[:s]) and e - s >= min_gap]
    if not real:
        return None
    s, e = max(real, key=lambda gap: gap[1] - gap[0])
    return (s + e) / 2


def _page_text(page: Any) -> str:
    """Read one page, column by column when it has two columns."""
    split = column_split(page.extract_words(), page.width)
    if split is None:
        return str(page.extract_text() or "")
    left = page.crop((0, 0, split, page.height)).extract_text() or ""
    right = page.crop((split, 0, page.width, page.height)).extract_text() or ""
    return f"{left}\n{right}"


def extract_text(pdf: bytes) -> str:
    """Return the CV's text, pages separated by blank lines.

    Raises `PdfError` if the PDF is encrypted or damaged, has more than `MAX_PAGES` pages, or has
    no text layer (a scanned document).
    """
    try:
        with pdfplumber.open(io.BytesIO(pdf)) as document:
            if len(document.pages) > MAX_PAGES:
                raise TOO_MANY_PAGES
            pages = [_page_text(page) for page in document.pages]
    except (PdfminerException, PSException) as error:
        raise UNREADABLE from error

    visible = sum(len(re.sub(r"\s", "", page)) for page in pages)
    if not pages or visible / len(pages) < MIN_CHARS_PER_PAGE:
        raise NO_TEXT
    return "\n\n".join(pages)
