"""Rater agreement and model evaluation for P1, as defined in research/annotation_protocol.md.

    uv run python evaluate.py agreement            # κ between the two raters, plus disagreements
    uv run python evaluate.py score <scores.csv>   # Spearman ρ of a model's scores vs our ratings
    uv run python evaluate.py compare ../../data/scores/*.csv   # every model against TF-IDF
    uv run python evaluate.py gaps <scores.csv>    # the pairs where model and ratings disagree most

`agreement` compares `research/ratings/kobi.csv` and `research/ratings/semanu.csv` (committed once
both of us have finished a batch, see the protocol) on the pairs both have rated: quadratic
weighted Cohen's κ (target ≥ 0.6), and every pair where the ratings differ by 2+.

`score` reads a CSV with `cv_id,jd_id,score` columns (e.g. `data/scores/tfidf-baseline.csv`),
joins it to the pairs both raters have rated, and reports Spearman ρ against the mean rating on the
**dev** split by default (`--split test` for the frozen final numbers), with a 95% bootstrap
confidence interval that resamples **job descriptions**, not pairs, because pairs that share a JD
aren't independent.

`compare` scores several models on the same pairs and puts each next to the baseline
(`tfidf-production.csv`, the deployed model) with **Δρ and its own 95% CI**, from a paired
bootstrap: each resample of JDs scores every model, so the CI is for the gap itself. That's the
ADR-0004 rule: a model replaces TF-IDF if its ρ is at least 0.55 and at least 0.10 above it.

`gaps` is the failure analysis for the model card: it puts the model's scores and our mean ratings
on the same 0–1 scale (percentile ranks, since only the order matters for ρ) and lists the pairs
where they disagree most, with which way the model is wrong. It prints IDs only, never CV or JD
text: read a pair in `data/pairs/packet-main.html` or the calibration packet.

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

from app.ml.metrics import LEVELS, ranks, spearman, weighted_kappa  # noqa: E402

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


BASELINE = "tfidf-production.csv"
TARGET_RHO, TARGET_GAIN = 0.55, 0.10  # ADR-0004 / project plan


def read_scores(path: Path) -> dict[tuple[str, str], float]:
    """Return (cv_id, jd_id) -> score from a `cv_id,jd_id,score` CSV."""
    with path.open(encoding="utf-8") as f:
        return {(r["cv_id"], r["jd_id"]): float(r["score"]) for r in csv.DictReader(f)}


def rated_by_jd(split: str) -> dict[str, list[tuple[tuple[str, str], float]]]:
    """JD -> [((cv_id, jd_id), mean rating)] for the pairs both raters rated in the split."""
    pairs = load_pairs()
    a, b = (read_ratings(r) for r in RATERS)
    by_jd: dict[str, list[tuple[tuple[str, str], float]]] = defaultdict(list)
    # Sorted: set order changes between runs, which would make the bootstrap unrepeatable.
    for pid in sorted(a.keys() & b.keys()):
        p = pairs[pid]
        if split == "all" or p["split"] == split:
            by_jd[p["jd_id"]].append(((p["cv_id"], p["jd_id"]), (a[pid] + b[pid]) / 2))
    if sum(map(len, by_jd.values())) < 3:
        raise SystemExit(f"fewer than 3 rated pairs in split '{split}'")
    return by_jd


def _rho(scores: dict[tuple[str, str], float], rows: list[tuple[tuple[str, str], float]]) -> float:
    return spearman([scores[key] for key, _ in rows], [rating for _, rating in rows])


def _bootstrap(
    by_jd: dict[str, list[tuple[tuple[str, str], float]]], rounds: int
) -> list[list[tuple[tuple[str, str], float]]]:
    """Resamples of JDs (with replacement), the same for every model so gaps are paired."""
    rng, jds = random.Random(0), sorted(by_jd)
    return [[x for jd in rng.choices(jds, k=len(jds)) for x in by_jd[jd]] for _ in range(rounds)]


def _ci(samples: list[float]) -> tuple[float, float]:
    ordered = sorted(samples)
    return ordered[int(0.025 * len(ordered))], ordered[int(0.975 * len(ordered)) - 1]


def score(path: Path, split: str, rounds: int) -> None:
    """Print Spearman ρ of model scores vs mean ratings, with a JD-level bootstrap CI."""
    by_jd, scores = rated_by_jd(split), read_scores(path)
    flat = [x for group in by_jd.values() for x in group]
    low, high = _ci([_rho(scores, sample) for sample in _bootstrap(by_jd, rounds)])
    print(f"{path.name} on {split}: {len(flat)} pairs from {len(by_jd)} JDs")
    rho = _rho(scores, flat)
    print(f"Spearman ρ = {rho:.3f}  (95% bootstrap CI over JDs: {low:.3f} to {high:.3f})")


def compare(paths: list[Path], split: str, rounds: int) -> None:
    """Print ρ for every model and its gap to the baseline, with paired bootstrap CIs."""
    baseline = next((p for p in paths if p.name == BASELINE), None)
    if baseline is None:
        raise SystemExit(f"include the baseline, {BASELINE}, among the score files")
    by_jd = rated_by_jd(split)
    flat = [x for group in by_jd.values() for x in group]
    samples = _bootstrap(by_jd, rounds)
    base = read_scores(baseline)
    base_rhos = [_rho(base, sample) for sample in samples]
    print(f"{split}: {len(flat)} pairs from {len(by_jd)} JDs, {rounds} bootstrap rounds over JDs")
    print(f"{'model':<28} {'ρ':>6}  {'95% CI':<15} {'Δρ vs TF-IDF':>12}  {'95% CI':<15} meets rule")
    for path in sorted(paths, key=lambda p: (p != baseline, p.name)):
        scores = read_scores(path)
        rho, rhos = _rho(scores, flat), [_rho(scores, sample) for sample in samples]
        low, high = _ci(rhos)
        line = f"{path.stem:<28} {rho:>6.3f}  {low:.3f} to {high:.3f}"
        if path == baseline:
            print(f"{line}  {'(baseline)':>12}")
            continue
        gain = rho - _rho(base, flat)
        g_low, g_high = _ci([m - b for m, b in zip(rhos, base_rhos, strict=True)])
        ok = rho >= TARGET_RHO and gain >= TARGET_GAIN
        print(f"{line}  {gain:>+12.3f}  {g_low:+.3f} to {g_high:+.3f} {'yes' if ok else 'no'}")
    rule = f"ρ ≥ {TARGET_RHO} and Δρ ≥ {TARGET_GAIN}"
    print(f"\nrule (ADR-0004): {rule}; read the Δρ CI before deciding")


def gaps(path: Path, split: str, top: int) -> None:
    """Print the pairs whose model rank and rating rank differ most."""
    pairs = {(p["cv_id"], p["jd_id"]): (pid, p) for pid, p in load_pairs().items()}
    rows = [x for group in rated_by_jd(split).values() for x in group]
    scores = read_scores(path)
    model = ranks([scores[key] for key, _ in rows])
    rated = ranks([rating for _, rating in rows])
    n = len(rows)

    def scale(r: float) -> float:
        return (r - 1) / (n - 1) if n > 1 else 0.0  # rank 1..n -> 0..1

    found = []
    for (key, rating), m, h in zip(rows, model, rated, strict=True):
        pid, pair = pairs[key]
        found.append((scale(m) - scale(h), pid, pair, rating, scores[key]))
    found.sort(key=lambda f: -abs(f[0]))
    print(f"{path.name} on {split}: the {min(top, n)} largest of {n} rank gaps (0–1 scale)")
    print(f"{'pair':<6} {'cv':<22} {'jd':<22} {'stratum':<10} {'rating':>6} {'score':>7}  gap")
    for gap, pid, pair, rating, value in found[:top]:
        way = "model too high" if gap > 0 else "model too low"
        print(
            f"{pid:<6} {pair['cv_id']:<22} {pair['jd_id']:<22} {pair['stratum']:<10} "
            f"{rating:>6.1f} {value:>7.4f}  {gap:+.2f} {way}"
        )


def main() -> None:
    """Parse the command line and run the chosen report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("agreement", help="κ between the two raters")
    sc = sub.add_parser("score", help="Spearman ρ of a model's scores")
    sc.add_argument("scores", type=Path)
    sc.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    sc.add_argument("--rounds", type=int, default=2000)
    cp = sub.add_parser("compare", help="ρ of several models and their gap to TF-IDF")
    cp.add_argument("scores", type=Path, nargs="+")
    cp.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    cp.add_argument("--rounds", type=int, default=2000)
    gp = sub.add_parser("gaps", help="pairs where the model and our ratings disagree most")
    gp.add_argument("scores", type=Path)
    gp.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    gp.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if args.command == "gaps":
        gaps(args.scores, args.split, args.top)
    elif args.command == "agreement":
        agreement()
    elif args.command == "compare":
        compare(args.scores, args.split, args.rounds)
    else:
        score(args.scores, args.split, args.rounds)


if __name__ == "__main__":
    main()
