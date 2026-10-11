# J2: rated pair set, agreement and evaluation

Tools for the rating workflow in [`research/annotation_protocol.md`](../../research/annotation_protocol.md).
Plain Python, no dependencies. Needs the corpus first (`scripts/k5-corpus`).

## 1. Build the pairs (once each, same result on both machines)

```bash
uv run python build_pairs.py
```

| Output (all git-ignored) | For | Contents |
|---|---|---|
| `data/pairs/pairs.jsonl` | scripts only, **don't open before rating** | 120 pairs with stratum, dev/test split, calibration flag |
| `data/pairs/packet-calibration.html` | raters | Pairs p001–p020: job description and CV side by side |
| `data/pairs/packet-main.html` | raters | Pairs p021–p120, after calibration |
| `data/ratings/<rater>.csv` | raters | Empty sheet `pair_id,rating,notes`. Never overwritten by a re-run |

What it guarantees:
- **Strata:** 60 same-field, 30 nearby-field, 30 unrelated. Every JD is in exactly 4 pairs, and each
  CV appears 3–5 times, so no single document dominates.
- **Split by JD:** 10 dev JDs (40 pairs) and 20 test JDs (80 pairs), every field in both.
- **Calibration:** 20 dev pairs (10 / 5 / 5 by stratum), IDs p001–p020.
- **Reproducible:** one seeded generator, so the same corpus gives the same pairs, IDs and split.

## 2. Rate the calibration batch (alone)

Open `packet-calibration.html` in a browser and fill in rows p001–p020 of your sheet. Don't
discuss pairs until both sheets are done.

## 3. Check agreement

```bash
uv run python evaluate.py agreement
```

Prints quadratic weighted Cohen's κ (target ≥ 0.6), exact and within-one agreement, and every pair
where you differ by 2 or more points: those are the ones to talk through before rating the rest.

## 4. Evaluate a model

```bash
uv run python evaluate.py score ../../data/scores/tfidf-baseline.csv            # dev (default)
uv run python evaluate.py score ../../data/scores/tfidf-baseline.csv --split test
```

Spearman ρ between the model's scores and the mean of our two ratings, with a 95% bootstrap CI that
resamples **job descriptions**, because pairs that share a JD aren't independent. Expect wide
intervals on dev (40 pairs from 10 JDs): use dev to compare settings, and run test once per model
version for the model card.

The κ and ρ functions are checked against scikit-learn's `cohen_kappa_score(weights="quadratic")` and
SciPy's `spearmanr` (identical to floating-point precision).
