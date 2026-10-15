"""Rater agreement and model evaluation for P1, as defined in research/annotation_protocol.md.

    uv run python evaluate.py agreement            # κ between the two raters, plus disagreements
    uv run python evaluate.py score <scores.csv>   # Spearman ρ of a model's scores vs our ratings

`agreement` compares `research/ratings/kobi.csv` and `research/ratings/semanu.csv` (committed once
both of us have finished a batch, see the protocol) on the pairs both have rated: quadratic
weighted Cohen's κ (target ≥ 0.6), and every pair where the ratings differ by 2+.

`score` reads a CSV with `cv_id,jd_id,score` columns (e.g. `data/scores/tfidf-baseline.csv`),
joins it to the pairs both raters have rated, and reports Spearman ρ against the mean rating on the
**dev** split by default (`--split test` for the frozen final numbers), with a 95% bootstrap
confidence interval that resamples **job descriptions**, not pairs, because pairs that share a JD
aren't independent.

The metric functions live in `backend/app/ml/metrics.py`, where CI tests them against
scikit-learn and SciPy reference values.
"""

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))  # use the tested metric code

from app.ml.metrics import LEVELS, spearman, weighted_kappa  # noqa: E402

PAIRS = ROOT / "data" / "pairs" / "pairs.jsonl"
RATINGS = ROOT / "research" / "ratings"  # shared copies; we rate in data/ratings/
RATERS = ("kobi", "semanu")


def read_ratings(rater: str) -> dict[str, int]:
    """Return pair_id -> rating for the rows this rater has filled in."""
    sheet = RATINGS / f"{rater}.csv"
    if not sheet.exists():
        raise SystemExit(f"{sheet.relative_to(ROOT)} is missing: commit it once both are done")
    with sheet.open(encoding="utf-8") as f:
        rows = csv.DictReader(f)
        ratings = {r["pair_id"]: int(r["rating"]) for r in rows if r["rating"].strip()}
    bad = {p: r for p, r in ratings.items() if r not in LEVELS}
    if bad:
        raise SystemExit(f"{rater}.csv has ratings outside 1-5: {bad}")
    return ratings


def load_pairs() -> dict[str, dict[str, str]]:
    """Return pair_id -> pair record."""
    with PAIRS.open(encoding="utf-8") as f:
        return {p["pair_id"]: p for p in map(json.loads, f)}


def agreement() -> None:
    """Print κ, the confusion of ratings and the pairs to discuss."""
    a, b = (read_ratings(r) for r in RATERS)
    both = sorted(a.keys() & b.keys())
    if not both:
        raise SystemExit("no pair rated by both raters yet")
    kappa = weighted_kappa([a[p] for p in both], [b[p] for p in both])
    exact = sum(a[p] == b[p] for p in both) / len(both)
    within1 = sum(abs(a[p] - b[p]) <= 1 for p in both) / len(both)
    print(f"pairs rated by both: {len(both)}")
    print(f"quadratic weighted κ: {kappa:.3f}  (target ≥ 0.6)")
    print(f"exact agreement: {exact:.0%}   within one point: {within1:.0%}")
    far = [p for p in both if abs(a[p] - b[p]) >= 2]
    print(f"\nto discuss ({len(far)} pairs differ by 2 or more):")
    for p in far:
        print(f"  {p}: {RATERS[0]} {a[p]}, {RATERS[1]} {b[p]}")


def score(path: Path, split: str, rounds: int) -> None:
    """Print Spearman ρ of model scores vs mean ratings, with a JD-level bootstrap CI."""
    pairs = load_pairs()
    a, b = (read_ratings(r) for r in RATERS)
    with path.open(encoding="utf-8") as f:
        scores = {(r["cv_id"], r["jd_id"]): float(r["score"]) for r in csv.DictReader(f)}

    by_jd: dict[str, list[tuple[float, float]]] = defaultdict(list)
    # Sorted: set order changes between runs, which would make the bootstrap unrepeatable.
    for pid in sorted(a.keys() & b.keys()):
        p = pairs[pid]
        if split != "all" and p["split"] != split:
            continue
        by_jd[p["jd_id"]].append((scores[(p["cv_id"], p["jd_id"])], (a[pid] + b[pid]) / 2))
    flat = [x for group in by_jd.values() for x in group]
    if len(flat) < 3:
        raise SystemExit(f"only {len(flat)} rated pairs in split '{split}'")

    rho = spearman([s for s, _ in flat], [r for _, r in flat])
    rng, jds, samples = random.Random(0), sorted(by_jd), []
    for _ in range(rounds):
        resampled = [x for jd in rng.choices(jds, k=len(jds)) for x in by_jd[jd]]
        samples.append(spearman([s for s, _ in resampled], [r for _, r in resampled]))
    samples.sort()
    low, high = samples[int(0.025 * rounds)], samples[int(0.975 * rounds) - 1]
    print(f"{path.name} on {split}: {len(flat)} pairs from {len(jds)} JDs")
    print(f"Spearman ρ = {rho:.3f}  (95% bootstrap CI over JDs: {low:.3f} to {high:.3f})")


def main() -> None:
    """Parse the command line and run the chosen report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("agreement", help="κ between the two raters")
    sc = sub.add_parser("score", help="Spearman ρ of a model's scores")
    sc.add_argument("scores", type=Path)
    sc.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    sc.add_argument("--rounds", type=int, default=2000)
    args = parser.parse_args()
    if args.command == "agreement":
        agreement()
    else:
        score(args.scores, args.split, args.rounds)


if __name__ == "__main__":
    main()
