# K5: evaluation corpus

Builds the P1 evaluation corpus: **30 job descriptions and 30 CVs** from the Djinni Recruitment
Dataset (MIT), 5 of each from six fields (Python, Data Science, JavaScript, Java, DevOps, QA).
Why this source: [ADR-0001](../../docs/adr/0001-data-sources.md). Details: [data card](../../docs/data_card.md).

## Run it

```bash
uv sync
uv run python build_corpus.py
```

The first run downloads about 380 MB into `data/raw/`. Later runs reuse it. Same seed and same
pinned revisions, so the same 60 records every time.

## Output (all in the repo's `data/`, git-ignored)

| File | Contents |
|---|---|
| `data/raw/djinni-*.parquet` | The two source files, checked against their SHA-256 |
| `data/corpus/jds.jsonl` | One JD per line: `id` (e.g. `jd-python-01`), `source_id`, `field`, `title`, `text`, `exp_years` |
| `data/corpus/cvs.jsonl` | One CV per line, same keys (`cv-python-01`, …) |
| `data/corpus/manifest.json` | Seed, source revisions and checksums, record counts, output checksums, PII placeholder counts |

Nothing here is committed. To share the exact corpus, share the commit: the script rebuilds it.
