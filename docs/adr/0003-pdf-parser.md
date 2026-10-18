# ADR-0003: PDF text extraction

**Status:** accepted by both deciders on 2026-10-18, without the planned rerun on real CVs (see
Consequences) · **Date:** 2026-10-09 · **Deciders:** Semanu (eng lead), Kobi (review)

## Context
`POST /api/v1/match` receives the CV as a PDF and needs its text in reading order. CVs often use two
columns (a sidebar beside the main column), and many tools store those lines row by row across the
page, so a naive extractor mixes the columns line by line. We also have to reject scanned
(image-only) and password-protected PDFs with a clear error, and stay well under Render Free's
512 MB (ADR-0002). The repo is MIT-licensed.

## Experiment (S6)
Harness: `scripts/s6-pdf-parsers/` (`make_fixtures.py`, `compare_parsers.py`). Six synthetic
CVs of a fictional person: one column, three pages, two columns stored column by column, the same
two columns stored row by row, a scanned copy (image only), and a password-protected file.
Accuracy is word-level similarity to the text drawn on the page; memory is the peak of the whole
Python process.

| Parser | Licence | One column | Two columns (column order) | Two columns (row order) | Scanned flagged | Encrypted | ms / file | Peak MB |
|---|---|---|---|---|---|---|---|---|
| pypdf 6.20 | BSD-3-Clause | 98% | 97% | **74%** | yes | clean error | 3 | 104 |
| pdfplumber 0.11 | MIT | 98% | **74%** | **74%** | yes | clean error | 12 | 93 |
| **pdfplumber + column split** | MIT | 98% | 97% | **97%** | yes | clean error | 12 | **80** |
| PyMuPDF 1.28 | AGPL-3.0 or commercial | 100% | 100% | **76%** | yes | clean error | 2 | 164 |
| PyMuPDF (sorted) | AGPL-3.0 or commercial | 100% | 76% | 76% | yes | clean error | 5 | 164 |

What the numbers show:
- **No library handles row-ordered two-column CVs on its own.** All of them interleave the columns
  (74–76%). Column handling has to be our code, whichever library we pick.
- The remaining 2–3% for pypdf and pdfplumber is only the bullet glyph: pdfplumber returns `•` as
  `(cid:127)`. Every word is extracted correctly; preprocessing strips `(cid:N)` tokens (K6).
- Scanned PDFs are caught by our own check, not the library: fewer than 25 visible characters per
  page on average means no usable text layer.
- Speed doesn't separate them: all are far below the 3 s budget.

## Options considered
1. **pdfplumber + our column split**: MIT, lowest memory, gives word positions, which the column
   split needs (find the empty vertical strip in the middle 60% of the page, then read each side).
   Cons: slowest of the three (still ~12 ms per page here); the split is our code to test and maintain.
2. **PyMuPDF**: fastest and most accurate on simple layouts. Cons: **AGPL-3.0** (or a paid
   licence): a service built on it must meet AGPL terms as a whole, including offering its full
   source to users, which sits badly with our MIT licence and limits how others can reuse our code.
   Twice the memory. Still interleaves row-ordered columns.
3. **pypdf**: BSD, fast. Cons: no convenient word positions, so the column split would be much more
   work; interleaves row-ordered columns.

## Decision
Use **pdfplumber with our column split**, wrapped in one function the API calls:
- Check the first bytes are `%PDF-` (else 415), the size is ≤ 5 MB (else 413) and pages ≤ 10.
- Encrypted or corrupted PDF → 422 `pdf_unreadable`.
- Fewer than 25 visible characters per page on average → 422 `pdf_no_text`.
- Two-column pages are read column by column; one-column pages as a whole.

## Consequences
- Permissive licences only (MIT/BSD), matching the repo's MIT licence.
- The column split and the text-layer check become backend code with unit tests. Done in
  `backend/app/extract.py`; the tests build their synthetic PDFs in memory (`backend/tests/pdfs.py`)
  instead of committing binary fixtures.
- **Correction found while implementing (2026-10-11):** taking the widest empty strip in the middle
  of the page fails when the right column has short lines, because the space after them is wider
  than the real gap. The backend version only accepts a gap with **text on both sides**
  (`test_column_split_ignores_empty_space_after_short_lines`). The S6 numbers above are unaffected:
  those fixtures had long lines in both columns.
- Preprocessing (K6) must remove `(cid:N)` placeholders.
- **Accepted without the real-CV rerun (2026-10-18).** We planned to rerun on 10 real CVs, including
  real two-column layouts, before accepting. That didn't happen: the evaluation corpus (K5) is plain
  text, not PDFs, and we don't handle real CVs. The decision rests on the S6 synthetic fixtures and
  the backend tests. Layouts we haven't checked (three columns, tables, text in boxes) are a known
  risk, tracked in #98; if they break the split, revisit here.

## Sources
- [pdfplumber](https://github.com/jsvine/pdfplumber) · [pypdf](https://github.com/py-pdf/pypdf) ·
  [PyMuPDF on PyPI (licence)](https://pypi.org/project/PyMuPDF/)
- Licences above were read from each installed package's metadata by `compare_parsers.py`.
