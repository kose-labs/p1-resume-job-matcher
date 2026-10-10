"""Compare embedding models for K8 / ADR-0004 on the evaluation corpus.

For each shortlisted model, scores all 900 CV–JD pairs two ways:

- **chunked**: the backend's `EmbeddingMatcher` (requirements × CV sentences, max similarity,
  weighted mean), the approach we plan to ship;
- **whole**: one vector per whole document, cosine of the two. The model silently truncates
  anything past its token limit, which is what chunking is meant to avoid.

Writes `data/scores/<model>-<mode>.csv` (git-ignored) for `scripts/j2-pairs/evaluate.py`, and
prints the field-label proxy (ROC AUC same-field vs unrelated / nearby) until our ratings exist.
Peak memory and load time are measured per model in a fresh process, as the API would load it.

    uv run python compare.py            # all models
    uv run python compare.py --memory bge-small   # one memory measurement (used internally)
"""

import argparse
import csv
import json
import resource
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))  # use the matcher exactly as the API will

from app.ml.embeddings import EmbeddingMatcher, Matrix  # noqa: E402
from app.ml.preprocess import clean_text  # noqa: E402

CORPUS = ROOT / "data" / "corpus"
SCORES = ROOT / "data" / "scores"
MODELS_DIR = Path(__file__).parent / "models"
NEARBY = {
    frozenset({"Python", "Data Science"}),
    frozenset({"Java", "JavaScript"}),
    frozenset({"QA", "DevOps"}),
}


def load_encoder(name: str) -> Callable[[Sequence[str]], Matrix]:
    """Load a shortlisted model and return a function from texts to embeddings."""
    if name == "potion-base-8m":
        from model2vec import StaticModel

        static = StaticModel.from_pretrained("minishlab/potion-base-8M")
        return lambda texts: np.asarray(static.encode(list(texts)), dtype=np.float32)
    from fastembed import TextEmbedding

    repo = {
        "bge-small": "BAAI/bge-small-en-v1.5",
        "minilm-l6": "sentence-transformers/all-MiniLM-L6-v2",
    }
    model = TextEmbedding(repo[name], cache_dir=str(MODELS_DIR))
    return lambda texts: np.vstack(list(model.embed(list(texts)))).astype(np.float32)


MODELS = ["potion-base-8m", "minilm-l6", "bge-small"]


class CachingEncoder:
    """Encode each distinct text once: a JD's requirements are reused across 30 CVs."""

    def __init__(self, encode: Callable[[Sequence[str]], Matrix]) -> None:
        """Wrap a raw encode function."""
        self._encode = encode
        self._cache: dict[str, np.ndarray] = {}

    def encode(self, texts: Sequence[str]) -> Matrix:
        """Return embeddings, computing only texts not seen before."""
        new = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if new:
            self._cache.update(zip(new, self._encode(new), strict=True))
        return np.vstack([self._cache[t] for t in texts])


def load(name: str) -> list[dict[str, str]]:
    """Read one JSONL file of the corpus."""
    with (CORPUS / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def relation(a: str, b: str) -> str:
    """Same field, nearby field or unrelated."""
    if a == b:
        return "same"
    return "nearby" if frozenset({a, b}) in NEARBY else "unrelated"


def auc(pos: list[float], neg: list[float]) -> float:
    """Probability a random positive outscores a random negative (ties count half)."""
    return sum((p > n) + 0.5 * (p == n) for p, n in product(pos, neg)) / (len(pos) * len(neg))


def write_scores(path: Path, rows: list[tuple[str, str, float]]) -> None:
    """Save `cv_id,jd_id,score` for the evaluation script."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cv_id", "jd_id", "score"])
        writer.writerows((c, j, f"{s:.4f}") for c, j, s in rows)


def proxy(cvs: list[dict[str, str]], jds: list[dict[str, str]], rows: list[tuple[str, str, float]]):
    """Return (AUC same vs unrelated, AUC same vs nearby, mean same, mean unrelated)."""
    field = {d["id"]: d["field"] for d in cvs + jds}
    groups: dict[str, list[float]] = {"same": [], "nearby": [], "unrelated": []}
    for c, j, s in rows:
        groups[relation(field[c], field[j])].append(s)
    return (
        auc(groups["same"], groups["unrelated"]),
        auc(groups["same"], groups["nearby"]),
        float(np.mean(groups["same"])),
        float(np.mean(groups["unrelated"])),
    )


def memory(name: str) -> None:
    """Load one model, match one pair, print load time and peak RSS (run in a fresh process)."""
    cvs, jds = load("cvs.jsonl"), load("jds.jsonl")
    start = time.perf_counter()
    matcher = EmbeddingMatcher(CachingEncoder(load_encoder(name)), name)
    loaded = time.perf_counter() - start
    start = time.perf_counter()
    matcher.match(cvs[0]["text"], jds[0]["text"])
    first = time.perf_counter() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(json.dumps({"load_s": loaded, "first_match_s": first, "peak_mb": peak}))


def main() -> None:
    """Score every pair with every model and mode, then print the comparison table."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory", choices=MODELS)
    args = parser.parse_args()
    if args.memory:
        memory(args.memory)
        return

    cvs, jds = load("cvs.jsonl"), load("jds.jsonl")
    SCORES.mkdir(parents=True, exist_ok=True)
    print(
        "| Model | Mode | AUC same/unrel | AUC same/nearby | Mean same | Mean unrel | "
        "Score 900 pairs | Load | First match | Peak RSS |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for name in MODELS:
        out = subprocess.run(
            [sys.executable, __file__, "--memory", name], capture_output=True, text=True, check=True
        )
        mem = json.loads(out.stdout.strip().splitlines()[-1])
        encoder = CachingEncoder(load_encoder(name))
        matcher = EmbeddingMatcher(encoder, name)

        start = time.perf_counter()
        chunked = [
            (c["id"], j["id"], matcher.match(c["text"], j["text"]).score)
            for c, j in product(cvs, jds)
        ]
        chunked_s = time.perf_counter() - start

        start = time.perf_counter()
        doc = {d["id"]: encoder.encode([clean_text(d["text"])])[0] for d in cvs + jds}
        unit = {k: v / (np.linalg.norm(v) or 1) for k, v in doc.items()}
        whole = [
            (c["id"], j["id"], float(max(0.0, unit[c["id"]] @ unit[j["id"]])))
            for c, j in product(cvs, jds)
        ]
        whole_s = time.perf_counter() - start

        for mode, rows, secs in (("chunked", chunked, chunked_s), ("whole", whole, whole_s)):
            write_scores(SCORES / f"{name}-{mode}.csv", rows)
            a_u, a_n, m_s, m_u = proxy(cvs, jds, rows)
            print(
                f"| {name} | {mode} | {a_u:.3f} | {a_n:.3f} | {m_s:.3f} | {m_u:.3f} "
                f"| {secs:.1f} s | {mem['load_s']:.1f} s | {mem['first_match_s'] * 1000:.0f} ms "
                f"| {mem['peak_mb']:.0f} MB |",
                flush=True,
            )


if __name__ == "__main__":
    main()
