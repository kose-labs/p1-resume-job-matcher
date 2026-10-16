# ADR-0004: Embedding model and matching approach

**Status:** proposed, decided on the dev ratings (2026-10-16); accepted when both deciders approve ·
**Date:** 2026-10-10, updated 2026-10-16 · **Deciders:** Kobi (ML lead), Semanu (review: memory and
latency)

## Context
After the TF-IDF baseline (K7), the plan (K8) is to match by meaning with sentence embeddings. Two
choices are open: **which model**, and **how to aggregate** (one vector per document, or requirement
× sentence chunks with max similarity). Constraints: Render Free's 512 MB RAM with the API's own
~130 MB (ADR-0002), the 3 s response target, permissive licences, and an English-only V1.

## Options considered
Shortlisted from MTEB English (model-card numbers); full results in
[`docs/experiments/k8-embeddings.md`](../experiments/k8-embeddings.md).

1. **all-MiniLM-L6-v2** (Apache-2.0, ONNX via fastembed): best on our proxy (AUC 0.794 whole,
   0.768 same-vs-nearby chunked), 247 MB peak, ~100 ms per match. Truncates at 256 tokens, so long
   JDs need chunking.
2. **potion-base-8M** (MIT, static model2vec): 129 MB peak, ~6 ms per match, no token limit; lowest
   MTEB and weaker on the proxy (0.685–0.743).
3. **bge-small-en-v1.5** (MIT, ONNX): highest MTEB (62.17) but weakest when chunked on our proxy
   (0.667) and the heaviest (286 MB, ~200 ms).
4. **Stay on TF-IDF**: as good as any embedding on the proxy (0.789), tiny and explainable; misses
   paraphrases, which the proxy can't measure.

Aggregation: **chunked** (requirements × CV sentences, max similarity, weighted mean; gives
per-requirement evidence for the API) or **whole** (one vector per document; simpler, but truncates
and gives no evidence).

## Result on the dev ratings (2026-10-16)
Both of us rated the 20 dev pairs of the main set; with the 20 calibration pairs that makes **40 dev
pairs from 10 JDs** (protocol v2). Agreement: quadratic weighted **κ = 0.770** (target ≥ 0.6), 92%
of pairs within one point. Each pair's label is the mean of our two ratings.

`scripts/j2-pairs/evaluate.py compare data/scores/*.csv --split dev`, 2,000 bootstrap rounds
resampling JDs; Δρ is each model's gap to the deployed TF-IDF, with a paired CI:

| Model | Spearman ρ | 95% CI | Δρ vs TF-IDF | 95% CI |
|---|---|---|---|---|
| **TF-IDF (production, ADR-0006)** | **0.660** | 0.414 to 0.815 | baseline | |
| bge-small, whole | 0.670 | 0.455 to 0.838 | +0.010 | −0.198 to +0.223 |
| MiniLM-L6, chunked | 0.657 | 0.465 to 0.771 | −0.003 | −0.174 to +0.153 |
| TF-IDF (K7 baseline, fitted on the corpus) | 0.631 | 0.364 to 0.810 | −0.029 | −0.112 to +0.072 |
| potion-base-8M, whole | 0.527 | 0.320 to 0.700 | −0.133 | −0.254 to +0.018 |
| MiniLM-L6, whole | 0.514 | 0.288 to 0.741 | −0.146 | −0.391 to +0.062 |
| bge-small, chunked | 0.440 | 0.196 to 0.674 | −0.219 | −0.472 to +0.019 |
| potion-base-8M, chunked | 0.436 | 0.195 to 0.642 | −0.223 | −0.438 to −0.016 |

The rule set before rating was **ρ ≥ 0.55 and Δρ ≥ 0.10**, preferring the simpler option when CIs
overlap. No embedding meets it: the best two are within ±0.01 of TF-IDF, and every chunked variant
except MiniLM is worse (potion chunked significantly so). The hybrid (whole similarity + requirement
coverage) wasn't run: with the best embedding level with TF-IDF, it would need a gain the components
don't show, and there is no time to tune it before launch. With 10 JDs the intervals are wide
(about ±0.2), so this says "no embedding is clearly better", not "TF-IDF is best".

## Decision
- **The score stays TF-IDF** (the production artefact of ADR-0006): ρ = 0.660 on dev clears the
  0.55 target, and no embedding beats it. It is also the smallest, fastest and most explainable.
- **No embedding model ships in V1.** The API's `evidence` stays empty, and the job's skills,
  matched and missing (K9, #65), explain the score instead. Embedding evidence would add `fastembed`
  and about 250 MB of peak memory against Render's 512 MB, untested in the API, two days before
  launch. **MiniLM-L6 chunked** (the best chunked model, and the one with evidence pairs) is the
  candidate for evidence in V1.1, after the memory test of S9.
- **Test is run once, on TF-IDF**, when the 80 test pairs are rated, for the model card.

## Consequences
- V1 adds no dependency and no memory. The points below apply if embeddings are added in V1.1:
- `fastembed` (onnxruntime, no PyTorch) joins the backend; image size and memory must be
  re-measured in the real API (S9: load once via lifespan, inject with `Depends`).
- Scores need calibrating before display (raw cosines cluster between 0.3 and 0.7).
- Model weights download at build time (Docker layer), not at request time, so cold starts don't
  fetch from the Hugging Face Hub. The model **revision is pinned and its hash checked**, so a
  rebuilt image can't silently pick up different weights.
- Memory is decided by measurement, not estimate (S9): the real API with the model loaded runs 4
  concurrent max-size matches in CI and fails above 400 MB peak RSS. Levers if it's tight:
  onnxruntime with 1 intra-op thread (Render Free has 0.1 CPU, so more threads only thrash) and a cap
  on concurrent model calls; potion-base-8M remains the fallback.
- The model card reports this result as it is: on our ratings, meaning-based matching didn't beat
  shared words, and chunking hurt most models.
