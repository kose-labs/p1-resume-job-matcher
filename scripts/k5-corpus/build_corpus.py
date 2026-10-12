"""Build the P1 evaluation corpus (K5): 30 job descriptions and 30 CVs from the Djinni dataset.

Choice of source and its trade-offs: docs/adr/0001-data-sources.md.

Steps:
1. Download the two Djinni parquet files at pinned revisions into `data/raw/` (skipped when
   already there) and check their SHA-256, so everyone samples from exactly the same bytes.
2. Sample 5 JDs and 5 CVs from each of six fields. The order is the MD5 of the record ID plus a
   fixed seed: deterministic, but unrelated to the dataset's own order.
3. Replace any e-mail address, phone number or URL left in the texts with a placeholder.
4. Write `data/corpus/jds.jsonl`, `data/corpus/cvs.jsonl` and `data/corpus/manifest.json`.

`data/` is git-ignored: the corpus is rebuilt from this script, never committed.

    uv run python build_corpus.py
"""

import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "corpus"

SEED = "kose-p1-k5"
PER_FIELD = 5
FIELDS = ["Python", "Data Science", "JavaScript", "Java", "DevOps", "QA"]
CITATION = (
    "Drushchak, N. and Romanyshyn, M. (2024). Introducing the Djinni Recruitment Dataset: "
    "A Corpus of Anonymized CVs and Job Postings. UNLP @ LREC-COLING 2024. "
    "https://aclanthology.org/2024.unlp-1.2"
)

SOURCES = {
    "jds": {
        "dataset": "lang-uk/recruitment-dataset-job-descriptions-english",
        "revision": "b56a6054c10f1266a141e37c8df66c79ff2863af",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "71dddaf0d9660f34ddf946953b67f54f1e7d60e22dcf9a4b8139b6378b18aab9",
        "file": "djinni-jds-en.parquet",
        "licence": "MIT",
    },
    "cvs": {
        "dataset": "lang-uk/recruitment-dataset-candidate-profiles-english",
        "revision": "86255174c6c378a2b52cd7e81d79002c64d899a6",
        "path": "data/train-00000-of-00001.parquet",
        "sha256": "a7b1378e0b231507c377659bf2c80fa4ba60c4e31e1107b13425d103879ecc3b",
        "file": "djinni-cvs-en.parquet",
        "licence": "MIT",
    },
}

# Long enough to say something about the job or the person, short enough to rate in a minute.
QUERIES = {
    "jds": """
        SELECT id, "Primary Keyword" AS field, Position AS title,
               "Long Description" AS text, "Exp Years" AS exp_years
        FROM read_parquet($file)
        WHERE "Primary Keyword" = $field
          AND "Long Description_lang" = 'en'
          AND length("Long Description") BETWEEN 600 AND 5000
        ORDER BY md5(id || $seed)
        LIMIT $n
    """,
    "cvs": """
        SELECT id, "Primary Keyword" AS field, Position AS title,
               CV AS text, CAST("Experience Years" AS VARCHAR) AS exp_years
        FROM read_parquet($file)
        WHERE "Primary Keyword" = $field
          AND CV_lang = 'en'
          AND length(CV) BETWEEN 400 AND 5000
        ORDER BY md5(id || $seed)
        LIMIT $n
    """,
}

# The dataset is anonymized; this is a second line of defence, and the counts go in the manifest.
PII_PATTERNS = {
    "[EMAIL]": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    "[URL]": re.compile(r"(?:https?://|www\.)\S+|\b(?:linkedin|github|t)\.(?:com|me)/\S+", re.I),
    "[PHONE]": re.compile(r"(?<!\w)[+(]?\d[\d ()\-]{8,}\d(?!\w)"),
}


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(source: dict[str, str]) -> Path:
    """Download a pinned parquet file once and verify its checksum."""
    target = RAW / source["file"]
    if not target.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/datasets/{source['dataset']}/resolve/"
            f"{source['revision']}/{source['path']}"
        )
        print(f"downloading {url}")
        partial = target.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=60) as resp, partial.open("wb") as f:
            while block := resp.read(1 << 20):
                f.write(block)
        partial.rename(target)
    if (actual := sha256(target)) != source["sha256"]:
        raise SystemExit(f"{target} has SHA-256 {actual}, expected {source['sha256']}. Delete it.")
    return target


def looks_like_phone(match: str) -> bool:
    """Tell a phone number from date ranges the pattern also matches, such as "2019 - 2021".

    A phone number has at least 9 digits, and its digit groups aren't all years.
    """
    groups = re.findall(r"\d+", match)
    years = all(len(g) == 4 and g.startswith(("19", "20")) for g in groups)
    return sum(map(len, groups)) >= 9 and not years


def scrub(text: str, counts: dict[str, int]) -> str:
    """Replace e-mails, URLs and phone numbers with placeholders, counting each kind."""
    for placeholder, pattern in PII_PATTERNS.items():

        def replace(m: re.Match[str], placeholder: str = placeholder) -> str:
            if placeholder == "[PHONE]" and not looks_like_phone(m.group()):
                return m.group()
            counts[placeholder] += 1
            return placeholder

        text = pattern.sub(replace, text)
    return text


def sample(kind: str, file: Path, counts: dict[str, int]) -> list[dict[str, str | None]]:
    """Sample PER_FIELD records per field, with stable IDs like `jd-python-01`."""
    records: list[dict[str, str | None]] = []
    con = duckdb.connect()
    prefix = kind[:-1]
    for field in FIELDS:
        params = {"file": str(file), "field": field, "seed": SEED, "n": PER_FIELD}
        rows = con.execute(QUERIES[kind], params).fetchall()
        if len(rows) < PER_FIELD:
            raise SystemExit(f"only {len(rows)} {kind} for {field}")
        slug = field.lower().replace(" ", "-")
        for i, (source_id, fld, title, text, exp_years) in enumerate(rows, start=1):
            records.append(
                {
                    "id": f"{prefix}-{slug}-{i:02d}",
                    "source_id": source_id,
                    "field": fld,
                    "title": scrub(title or "", counts),
                    "text": scrub(text, counts),
                    "exp_years": exp_years,
                }
            )
    return records


def main() -> None:
    """Download, sample, scrub and write the corpus with its manifest."""
    OUT.mkdir(parents=True, exist_ok=True)
    counts = dict.fromkeys(PII_PATTERNS, 0)
    files: dict[str, object] = {}
    manifest: dict[str, object] = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": SEED,
        "fields": FIELDS,
        "per_field": PER_FIELD,
        "citation": CITATION,
        "files": files,
    }
    for kind, source in SOURCES.items():
        records = sample(kind, download(source), counts)
        out = OUT / f"{kind}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        files[out.name] = {
            "records": len(records),
            "sha256": sha256(out),
            "source": {k: source[k] for k in ("dataset", "revision", "sha256", "licence")},
        }
        print(f"wrote {len(records)} {kind} to {out.relative_to(ROOT)}")
    manifest["pii_replacements"] = counts
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"PII placeholders inserted: {counts}")


if __name__ == "__main__":
    main()
