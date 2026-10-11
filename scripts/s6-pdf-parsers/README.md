# S6: PDF parser comparison

Experiment behind ADR-0003. Compares pypdf, pdfplumber (with and without our column split) and
PyMuPDF on synthetic CVs, and optionally on real CVs kept only on your machine.

## Run it (PowerShell, one command per line)

```powershell
uv sync
uv run python make_fixtures.py
uv run python compare_parsers.py
```

Results print to the terminal and are saved to `results.md`.

## Adding real CVs

1. Create a `cvs` folder here and put the PDFs in it. It is git-ignored: **real CVs never get
   committed.**
2. Run `uv run python compare_parsers.py` again.
3. Read the extracted text in `out/<parser>/` (also git-ignored) and check that two-column CVs come
   out column by column, not mixed line by line.
4. Delete `cvs/` and `out/` when you're done if the CVs aren't yours.

## Files

| File | What it does |
|---|---|
| `make_fixtures.py` | Writes six synthetic CVs (fictional person) and `fixtures/truth.json` |
| `compare_parsers.py` | Runs each parser in its own process; measures accuracy, scanned/encrypted handling, speed and peak memory |
| `results.md` | Latest results table |
