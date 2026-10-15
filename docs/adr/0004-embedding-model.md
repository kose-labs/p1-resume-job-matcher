# ADR-0004: Embedding model and matching approach

**Status:** proposed: decide on the dev ratings (J2) · **Date:** 2026-10-10 · **Deciders:** Kobi
(ML lead), Semanu (review: memory and latency)

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

## Decision (proposed)
- **Candidate model: all-MiniLM-L6-v2**, with **potion-base-8M as the fallback** if memory or
  latency on Render is a problem. bge-small is dropped: heaviest and not better on our data.
- **Keep the chunked matcher in the API regardless**, because the `evidence` field in the API
  contract needs requirement-to-sentence pairs.
- **The score itself is decided on the dev ratings**, comparing Spearman ρ for: TF-IDF, MiniLM
  chunked, MiniLM whole, potion chunked / whole, and a hybrid (whole similarity + requirement
  coverage), each with a JD-level bootstrap CI (`scripts/j2-pairs/evaluate.py`). Prefer the simpler
  option when CIs overlap. Then run test once and update this ADR to **accepted**.

## Consequences
- Adds `fastembed` (onnxruntime, no PyTorch) to the backend when accepted; image size and memory
  must be re-measured in the real API (S9: load once via lifespan, inject with `Depends`).
- Scores need calibrating before display (raw cosines cluster between 0.3 and 0.7).
- Model weights download at build time (Docker layer), not at request time, so cold starts don't
  fetch from the Hugging Face Hub. The model **revision is pinned and its hash checked**, so a
  rebuilt image can't silently pick up different weights.
- Memory is decided by measurement, not estimate (S9): the real API with the model loaded runs 4
  concurrent max-size matches in CI and fails above 400 MB peak RSS. Levers if it's tight:
  onnxruntime with 1 intra-op thread (Render Free has 0.1 CPU, so more threads only thrash) and a cap
  on concurrent model calls; potion-base-8M remains the fallback.
- If no embedding beats TF-IDF on dev, we ship TF-IDF for the score, keep embeddings for evidence,
  and report that honestly in the model card.
