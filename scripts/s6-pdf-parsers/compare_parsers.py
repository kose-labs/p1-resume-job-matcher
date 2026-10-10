"""Compare pypdf, pdfplumber and PyMuPDF on CV PDFs for ADR-0003.

For each parser, in a fresh process so memory numbers don't mix:
- accuracy: word-level similarity to the ground truth (synthetic fixtures only),
- reading order: two-column CVs score low if the columns get interleaved,
- scanned PDFs: whether the "no text layer" check flags them,
- encrypted PDFs: whether the parser fails cleanly,
- speed (median of 5 runs) and peak memory of the whole process.

Real CVs placed in `cvs/` (git-ignored) are also timed, and their extracted text is written to
`out/<parser>/` (git-ignored) for reading by eye. Results go to `results.md`.
"""

import json
import multiprocessing as mp
import re
import statistics
import time
from collections.abc import Callable
from difflib import SequenceMatcher
from importlib.metadata import metadata, version
from pathlib import Path

import psutil

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
REAL_CVS = HERE / "cvs"
OUT = HERE / "out"
RUNS = 5
# Fewer visible characters than this per page means there is no usable text layer.
MIN_CHARS_PER_PAGE = 25

PACKAGES = {
    "pypdf": "pypdf",
    "pdfplumber": "pdfplumber",
    "pdfplumber-columns": "pdfplumber",
    "pymupdf": "PyMuPDF",
    "pymupdf-sorted": "PyMuPDF",
}


class UnreadablePdf(Exception):
    """The PDF is encrypted or corrupted."""


def extract_pypdf(path: Path) -> list[str]:
    """Return the text of each page using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    if reader.is_encrypted:
        raise UnreadablePdf("encrypted")
    return [page.extract_text() or "" for page in reader.pages]


def extract_pdfplumber(path: Path) -> list[str]:
    """Return the text of each page using pdfplumber."""
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def column_split(words: list[dict], width: float, min_gap: float = 15) -> float | None:
    """Return the x position of the gap between two columns, or None for a one-column page.

    Marks every horizontal point covered by a word, then looks for the widest uncovered strip in
    the middle 60% of the page. One-column pages have no such strip because full-width lines
    cover it.
    """
    covered = [False] * (int(width) + 2)
    for word in words:
        for x in range(int(word["x0"]), int(word["x1"]) + 1):
            covered[x] = True
    best, start = (0, 0), None
    for x in range(int(width * 0.2), int(width * 0.8) + 1):
        if not covered[x] and start is None:
            start = x
        elif covered[x] and start is not None:
            best = max(best, (start, x), key=lambda gap: gap[1] - gap[0])
            start = None
    if start is not None:
        best = max(best, (start, int(width * 0.8)), key=lambda gap: gap[1] - gap[0])
    return (best[0] + best[1]) / 2 if best[1] - best[0] >= min_gap else None


def extract_pdfplumber_columns(path: Path) -> list[str]:
    """Return the text of each page using pdfplumber, reading two-column pages column by column."""
    import pdfplumber

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            split = column_split(page.extract_words(), page.width)
            if split is None:
                pages.append(page.extract_text() or "")
                continue
            left = page.crop((0, 0, split, page.height)).extract_text() or ""
            right = page.crop((split, 0, page.width, page.height)).extract_text() or ""
            pages.append(f"{left}\n{right}")
    return pages


def extract_pymupdf(path: Path, sort: bool = False) -> list[str]:
    """Return the text of each page using PyMuPDF, optionally sorted into reading order."""
    import pymupdf

    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise UnreadablePdf("encrypted")
        return [page.get_text("text", sort=sort) for page in doc]


EXTRACTORS: dict[str, Callable[[Path], list[str]]] = {
    "pypdf": extract_pypdf,
    "pdfplumber": extract_pdfplumber,
    "pdfplumber-columns": extract_pdfplumber_columns,
    "pymupdf": extract_pymupdf,
    "pymupdf-sorted": lambda path: extract_pymupdf(path, sort=True),
}


def has_text_layer(pages: list[str]) -> bool:
    """Return True if the average page has enough visible characters to be a text PDF."""
    visible = sum(len(re.sub(r"\s", "", page)) for page in pages)
    return bool(pages) and visible / len(pages) >= MIN_CHARS_PER_PAGE


def words(text: str) -> list[str]:
    """Split text into words, ignoring layout whitespace and bullet characters."""
    return text.replace("•", " ").split()


def accuracy(pages: list[str], orders: list[list[str]]) -> float:
    """Return the best word-level similarity between the extraction and any valid reading order."""
    got = words("\n".join(pages))
    return max(SequenceMatcher(None, words("\n".join(order)), got).ratio() for order in orders)


def peak_rss_mb() -> float:
    """Return this process's peak memory in MB (peak working set on Windows)."""
    info = psutil.Process().memory_info()
    return getattr(info, "peak_wset", info.rss) / 1_048_576


def run_parser(name: str, files: list[Path], queue: "mp.Queue[dict[str, object]]") -> None:
    """Measure one parser on every file; runs in its own process."""
    extract = EXTRACTORS[name]
    rows: dict[str, dict[str, object]] = {}
    for path in files:
        times: list[float] = []
        pages: list[str] = []
        error = ""
        for _ in range(RUNS):
            start = time.perf_counter()
            try:
                pages = extract(path)
            except Exception as exc:  # recording how each parser fails is the point here
                error = type(exc).__name__
                break
            times.append((time.perf_counter() - start) * 1000)
        rows[path.name] = {
            "pages": pages,
            "error": error,
            "ms": statistics.median(times) if times else None,
        }
    queue.put({"name": name, "rows": rows, "peak_mb": peak_rss_mb()})


def licence(package: str) -> str:
    """Return the licence a package declares in its metadata."""
    meta = metadata(package)
    expression = meta.get("License-Expression")
    if expression:
        return expression
    declared = " ".join(
        [meta.get("License") or ""]
        + [c for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    )
    if "AFFERO" in declared.upper():
        return "AGPL-3.0 or commercial"
    if "MIT" in declared:
        return "MIT"
    return declared.split(" :: ")[-1][:40] or "unknown"


def main() -> None:
    """Run every parser and write results.md."""
    truth: dict[str, dict] = json.loads((FIXTURES / "truth.json").read_text("utf-8"))
    fixture_files = [FIXTURES / name for name in truth]
    real_files = sorted(REAL_CVS.glob("*.pdf")) if REAL_CVS.exists() else []

    results = []
    for name in EXTRACTORS:
        queue: mp.Queue[dict[str, object]] = mp.Queue()
        proc = mp.Process(target=run_parser, args=(name, fixture_files + real_files, queue))
        proc.start()
        results.append(queue.get())
        proc.join()

    lines = [
        "# S6 results: PDF parser comparison",
        "",
        f"Synthetic fixtures ({len(fixture_files)}) and real CVs ({len(real_files)}). "
        f"Times are the median of {RUNS} runs; memory is the peak of the whole Python process "
        "(interpreter + library + extraction).",
        "",
        "| Parser | Version · licence | One column | Two columns (column order) "
        "| Two columns (row order) | 3 pages | Scanned PDF flagged | Encrypted "
        "| Median ms / file | Peak MB |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for res in results:
        rows = res["rows"]
        package = PACKAGES[res["name"]]

        def score(file: str, rows: dict = rows) -> str:
            row = rows[file]
            if row["error"]:
                return f"error: {row['error']}"
            return f"{accuracy(row['pages'], truth[file]['orders']):.0%}"

        scanned = rows["image_only.pdf"]
        flagged = "yes" if not scanned["error"] and not has_text_layer(scanned["pages"]) else "no"
        enc = rows["encrypted.pdf"]
        enc_result = f"fails cleanly ({enc['error']})" if enc["error"] else "no error raised"
        timed = [r["ms"] for f, r in rows.items() if r["ms"] is not None and f != "encrypted.pdf"]
        lines.append(
            f"| {res['name']} | {version(package)} · {licence(package)} "
            f"| {score('one_column.pdf')} | {score('two_column.pdf')} "
            f"| {score('two_column_rows.pdf')} | {score('multi_page.pdf')} "
            f"| {flagged} | {enc_result} | {statistics.median(timed):.1f} | {res['peak_mb']:.0f} |"
        )

        for path in real_files:
            target = OUT / res["name"] / f"{path.stem}.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n\f\n".join(rows[path.name]["pages"]), "utf-8")

    lines += [
        "",
        "Accuracy is word-level similarity to the text drawn on the page. For the two-column CV, "
        "either column first counts as correct; interleaved columns score low.",
    ]
    if real_files:
        lines.append(f"Extracted text from the real CVs is in `{OUT.name}/` for checking by eye.")
    (HERE / "results.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
