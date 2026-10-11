"""CV text extraction (ADR-0003): reading order, scanned and damaged PDFs, page limit."""

import pytest

from app.extract import MAX_PAGES, PdfError, column_split, extract_text
from tests.pdfs import MAIN, SIDEBAR, TEXT_PDF, image_only_pdf, text_pdf, two_column_rows_pdf


def error_code(pdf: bytes) -> str:
    with pytest.raises(PdfError) as error:
        extract_text(pdf)
    return error.value.code


def test_one_column_text_is_extracted() -> None:
    text = extract_text(TEXT_PDF)
    assert "Built FastAPI services in Python with PostgreSQL and Docker." in text
    assert "C++" in text and "C#" in text


def test_two_column_cv_is_read_column_by_column() -> None:
    lines = [line for line in extract_text(two_column_rows_pdf()).splitlines() if line.strip()]
    # Each column comes out whole and in order, not interleaved line by line.
    assert lines == SIDEBAR + MAIN


def test_pages_are_joined_with_blank_lines() -> None:
    assert extract_text(text_pdf(pages=2)).count("JORDAN EXAMPLE") == 2


def test_scanned_pdf_is_rejected() -> None:
    assert error_code(image_only_pdf()) == "pdf_no_text"


def test_password_protected_pdf_is_rejected() -> None:
    assert error_code(text_pdf(password="not-the-password")) == "pdf_unreadable"


def test_damaged_pdf_is_rejected() -> None:
    assert error_code(b"%PDF-1.7\n this is not really a pdf") == "pdf_unreadable"
    assert error_code(TEXT_PDF[:200]) == "pdf_unreadable"


def test_too_many_pages_is_rejected_before_reading_them() -> None:
    assert error_code(text_pdf(pages=MAX_PAGES + 1)) == "pdf_too_many_pages"


def test_ten_pages_is_still_allowed() -> None:
    assert extract_text(text_pdf(pages=MAX_PAGES)).count("JORDAN EXAMPLE") == MAX_PAGES


def test_column_split_finds_no_gap_on_full_width_lines() -> None:
    words = [{"x0": 50, "x1": 550}]
    assert column_split(words, width=600) is None


def test_column_split_finds_the_gap_between_columns() -> None:
    words = [{"x0": 30, "x1": 150}, {"x0": 220, "x1": 560}]
    assert column_split(words, width=600) == pytest.approx(185, abs=1)


def test_column_split_ignores_empty_space_after_short_lines() -> None:
    # Right column of short lines: the strip after them (380-480) is wider than the real gap
    # (150-220), but has no text to its right, so it isn't a column gap.
    words = [{"x0": 30, "x1": 150}, {"x0": 220, "x1": 380}]
    assert column_split(words, width=600) == pytest.approx(185, abs=1)


def test_column_split_ignores_words_outside_the_page() -> None:
    words = [{"x0": -20, "x1": 150}, {"x0": 220, "x1": 700}]
    assert column_split(words, width=600) is not None
