"""Score every CV–JD pair of the evaluation corpus with the TF-IDF baseline (K7).

Reads `data/corpus/{cvs,jds}.jsonl` (built by `scripts/k5-corpus`), fits the vectorizer once on
all 60 texts, scores all 900 pairs and writes `data/scores/tfidf-baseline.csv` (git-ignored) for
the evaluation.

Until the rated pairs exist (J2) there is no Spearman ρ yet, so it also prints a sanity check:
how well the score separates same-field pairs from unrelated ones (ROC AUC, 0.5 = chance).

Run from `backend/`:  uv run python -m scripts.score_corpus
"""

import csv
import json
from itertools import product
from pathlib import Path

from app.ml.tfidf import TfidfMatcher

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"
OUT = ROOT / "data" / "scores" / "tfidf-baseline.csv"
# Fields close enough that a pair could be a partial match (annotation protocol, "nearby").
NEARBY = {
    frozenset({"Python", "Data Science"}),
    frozenset({"Java", "JavaScript"}),
    frozenset({"QA", "DevOps"}),
}


def load(name: str) -> list[dict[str, str]]:
    """Read one JSONL file of the corpus."""
    with (CORPUS / name).open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def relation(cv_field: str, jd_field: str) -> str:
    """Classify a pair as same-field, nearby or unrelated."""
    if cv_field == jd_field:
        return "same"
    return "nearby" if frozenset({cv_field, jd_field}) in NEARBY else "unrelated"


def auc(positives: list[float], negatives: list[float]) -> float:
    """Probability that a random positive scores above a random negative (ties count half)."""
    wins = sum((p > n) + 0.5 * (p == n) for p, n in product(positives, negatives))
    return wins / (len(positives) * len(negatives))


def main() -> None:
    """Fit on the corpus, score all pairs, write the CSV and print the sanity check."""
    cvs, jds = load("cvs.jsonl"), load("jds.jsonl")
    matcher = TfidfMatcher().fit([d["text"] for d in cvs + jds])
    scores = matcher.score_matrix([d["text"] for d in cvs], [d["text"] for d in jds])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    by_relation: dict[str, list[float]] = {"same": [], "nearby": [], "unrelated": []}
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["cv_id", "jd_id", "relation", "score"])
        for (i, cv), (j, jd) in product(enumerate(cvs), enumerate(jds)):
            rel = relation(cv["field"], jd["field"])
            score = float(scores[i, j])
            by_relation[rel].append(score)
            writer.writerow([cv["id"], jd["id"], rel, f"{score:.4f}"])

    print(
        f"{matcher.name} {matcher.version}: {len(cvs) * len(jds)} pairs -> {OUT.relative_to(ROOT)}"
    )
    print(f"vocabulary: {len(matcher.vectorizer.vocabulary_)} terms (1-2 grams)")
    for rel, values in by_relation.items():
        values.sort()
        mean, median = sum(values) / len(values), values[len(values) // 2]
        print(f"{rel:>9}: n={len(values):3d}  mean={mean:.3f}  median={median:.3f}")
    print(f"AUC same vs unrelated: {auc(by_relation['same'], by_relation['unrelated']):.3f}")
    print(f"AUC same vs nearby:    {auc(by_relation['same'], by_relation['nearby']):.3f}")


if __name__ == "__main__":
    main()
