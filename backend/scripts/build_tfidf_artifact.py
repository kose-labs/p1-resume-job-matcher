"""Build the production TF-IDF artefact from public job descriptions only (S9, ADR-0006).

The deployed matcher needs IDF weights fitted on a corpus, but CVs are personal data that never
leave our machines (ADR-0001), so the corpus is **job descriptions only**: a fixed sample of the
Djinni English job postings (MIT), excluding the 30 job descriptions in our evaluation set so the
test numbers aren't flattered. Only the fitted vocabulary and weights are written, not the texts.

Run from `backend/` (the first run downloads 139 MB into the git-ignored `data/raw/`):

    uv run python -m scripts.build_tfidf_artifact

Same seed, same pinned revision and same code give a byte-identical artefact.
"""

import hashlib
import urllib.request
from pathlib import Path

import duckdb

from app.ml.tfidf import TfidfMatcher

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
ARTIFACT = Path(__file__).resolve().parents[1] / "app" / "ml" / "artifacts" / "tfidf-jds.json.gz"

# Same pinned file as scripts/k5-corpus (ADR-0001), so both share the download.
SOURCE = {
    "dataset": "lang-uk/recruitment-dataset-job-descriptions-english",
    "revision": "b56a6054c10f1266a141e37c8df66c79ff2863af",
    "path": "data/train-00000-of-00001.parquet",
    "sha256": "71dddaf0d9660f34ddf946953b67f54f1e7d60e22dcf9a4b8139b6378b18aab9",
    "file": "djinni-jds-en.parquet",
    "licence": "MIT",
    "citation": "Drushchak, N. and Romanyshyn, M. (2024). Introducing the Djinni Recruitment "
    "Dataset. UNLP @ LREC-COLING 2024. https://aclanthology.org/2024.unlp-1.2",
}
SAMPLE_SIZE = 3000
SEED = "kose-p1-tfidf"
PARAMS = {"ngram_range": (1, 2), "min_df": 2, "max_features": 50_000}

# The evaluation corpus's selection (scripts/k5-corpus/build_corpus.py), reproduced so those
# 30 job descriptions are left out of the production fit.
EVAL_SEED = "kose-p1-k5"
EVAL_FIELDS = ["Python", "Data Science", "JavaScript", "Java", "DevOps", "QA"]
EVAL_PER_FIELD = 5
ENGLISH_AND_SIZED = """
    "Long Description_lang" = 'en' AND length("Long Description") BETWEEN 600 AND 5000
"""


def sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download() -> Path:
    """Download the pinned parquet file once and verify its checksum."""
    target = RAW / SOURCE["file"]
    if not target.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        url = (
            f"https://huggingface.co/datasets/{SOURCE['dataset']}/resolve/"
            f"{SOURCE['revision']}/{SOURCE['path']}"
        )
        print(f"downloading {url}")
        partial = target.with_suffix(".part")
        with urllib.request.urlopen(url, timeout=60) as resp, partial.open("wb") as f:
            while block := resp.read(1 << 20):
                f.write(block)
        partial.rename(target)
    if (actual := sha256(target)) != SOURCE["sha256"]:
        raise SystemExit(f"{target} has SHA-256 {actual}, expected {SOURCE['sha256']}. Delete it.")
    return target


def evaluation_ids(con: duckdb.DuckDBPyConnection, file: Path) -> list[str]:
    """IDs of the 30 evaluation job descriptions, selected exactly as the corpus script does."""
    ids: list[str] = []
    for field in EVAL_FIELDS:
        rows = con.execute(
            f"""SELECT id FROM read_parquet($file)
                WHERE "Primary Keyword" = $field AND {ENGLISH_AND_SIZED}
                ORDER BY md5(id || $seed) LIMIT $n""",
            {"file": str(file), "field": field, "seed": EVAL_SEED, "n": EVAL_PER_FIELD},
        ).fetchall()
        ids += [str(row[0]) for row in rows]
    return ids


def sample_texts(con: duckdb.DuckDBPyConnection, file: Path, exclude: list[str]) -> list[str]:
    """A fixed sample of English job descriptions, leaving out the evaluation set."""
    rows = con.execute(
        f"""SELECT "Long Description" FROM read_parquet($file)
            WHERE {ENGLISH_AND_SIZED} AND NOT list_contains($exclude, CAST(id AS VARCHAR))
            ORDER BY md5(id || $seed) LIMIT $n""",
        {"file": str(file), "exclude": exclude, "seed": SEED, "n": SAMPLE_SIZE},
    ).fetchall()
    return [str(row[0]) for row in rows]


def main() -> None:
    """Download, sample, fit and write the artefact with its provenance."""
    file = download()
    con = duckdb.connect()
    excluded = evaluation_ids(con, file)
    texts = sample_texts(con, file, excluded)
    if len(texts) < SAMPLE_SIZE or len(excluded) != len(EVAL_FIELDS) * EVAL_PER_FIELD:
        raise SystemExit(f"sampled {len(texts)} texts, excluded {len(excluded)} evaluation JDs")

    matcher = TfidfMatcher(**PARAMS).fit(texts)  # type: ignore[arg-type]
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    matcher.save(
        ARTIFACT,
        {
            "source": {
                k: SOURCE[k] for k in ("dataset", "revision", "sha256", "licence", "citation")
            },
            "sample": {
                "documents": len(texts),
                "seed": SEED,
                "filter": "English, 600-5,000 characters",
                "excluded_evaluation_jds": len(excluded),
            },
            "params": {"min_df": PARAMS["min_df"], "max_features": PARAMS["max_features"]},
        },
    )
    vocabulary = len(matcher.vectorizer.vocabulary_)
    size_kb = ARTIFACT.stat().st_size / 1024
    print(f"fitted on {len(texts)} job descriptions ({len(excluded)} evaluation JDs excluded)")
    print(f"vocabulary: {vocabulary} terms; wrote {ARTIFACT.name}: {size_kb:.0f} KB")
    print(f"sha256: {sha256(ARTIFACT)}")


if __name__ == "__main__":
    main()
