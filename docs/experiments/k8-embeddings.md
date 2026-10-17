# K8: sentence embeddings with chunking

**Owner:** Kobi · **Date:** 2026-10-10 · **Code:** `backend/app/ml/embeddings.py`,
`scripts/k8-embeddings/compare.py` · **Decision:** [ADR-0004](../adr/0004-embedding-model.md): TF-IDF stays the score; decided on the dev ratings

## Hypothesis
Pretrained sentence embeddings rank CV–JD pairs closer to human judgement than TF-IDF (K7), because
they match meaning rather than exact words. Matching each JD requirement to its best CV sentence
(**chunked**) should beat one vector per whole document (**whole**), because whole-document vectors
blur everything together and models truncate long texts.

## Setup
- **Corpus:** 30 JDs × 30 CVs = 900 pairs (K5); same preprocessing as K7 (K6).
- **Models** (shortlisted from MTEB English, numbers from the model cards; all small enough for
  Render Free's 512 MB):

| Model | Type | Size | MTEB avg | STS | Retrieval | Max tokens | Licence |
|---|---|---|---|---|---|---|---|
| [bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | transformer (ONNX, fastembed) | 33M params | 62.17 | 81.59 | 51.68 | 512 | MIT |
| [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) | transformer (ONNX, fastembed) | 22M params | 55.93 | 78.95 | 42.92 | 256 | Apache-2.0 |
| [potion-base-8M](https://huggingface.co/minishlab/potion-base-8M) | static (model2vec, no neural network at run time) | 8M params | 51.08 | 72.91 | 31.11 | none | MIT |

- **Chunked:** JD → requirement sentences (benefits / company sections skipped, nice-to-have weight
  0.5); CV → sentences, long ones as 64-word windows with 16 words of overlap. Score = weighted mean
  over requirements of the best cosine similarity with any CV sentence.
- **Whole:** one embedding per cleaned document, cosine of the two (models truncate past their limit).
- **Metric for now:** the same field-label proxy as K7 (ROC AUC of same-field vs unrelated / nearby
  pairs). **The real metric, Spearman ρ against our ratings on dev, comes after J2:** run
  `scripts/j2-pairs/evaluate.py score data/scores/<model>-<mode>.csv` for each file below.
- **Cost:** peak RSS of a fresh process that imports the matcher, loads the model and matches one
  pair; time to score all 900 pairs with each text embedded once (cached).

## Results

| Model | Mode | AUC same vs unrelated | AUC same vs nearby | Mean score same / unrelated | 900 pairs | First match | Peak RSS |
|---|---|---|---|---|---|---|---|
| TF-IDF (K7, reference) | — | **0.789** | **0.760** | 0.038 / 0.020 | < 1 s | — | 132 MB* |
| potion-base-8M | chunked | 0.685 | 0.685 | 0.346 / 0.305 | 0.7 s | 6 ms | **129 MB** |
| potion-base-8M | whole | 0.743 | 0.743 | 0.671 / 0.589 | < 0.1 s | 6 ms | 129 MB |
| all-MiniLM-L6-v2 | chunked | 0.755 | **0.768** | 0.351 / 0.296 | 3.5 s | 100 ms | 247 MB |
| all-MiniLM-L6-v2 | whole | **0.794** | 0.755 | 0.472 / 0.348 | 0.8 s | 100 ms | 247 MB |
| bge-small-en-v1.5 | chunked | 0.667 | 0.650 | 0.630 / 0.605 | 5.5 s | 200 ms | 286 MB |
| bge-small-en-v1.5 | whole | 0.774 | 0.734 | 0.712 / 0.650 | 2.2 s | 200 ms | 286 MB |

\* TF-IDF's figure includes the API (FastAPI) and scikit-learn; the embedding figures include only the
matcher and the model, so the API adds roughly 90 MB to each.

## Conclusion (provisional, until rated pairs exist)
1. **The hypothesis isn't supported on the proxy.** No embedding setup clearly beats TF-IDF; the best,
   MiniLM whole (0.794), is within noise of it (0.789). Chunked scores below whole for every model.
2. **Why chunking may look worse here, and why that might not hold on our ratings.** The proxy
   rewards "same topic", which whole-document vectors capture well. Chunked scoring measures
   requirement coverage, and generic requirements ("upper-intermediate English", "team player",
   "good communication") find a decent match in almost any CV. That compresses the scores (mean same
   0.35 vs unrelated 0.30 for MiniLM). Whether coverage or topic tracks real fit is exactly what
   our ratings decide.
3. **A bigger MTEB score didn't help.** bge-small, the strongest on MTEB, is the weakest here when chunked and
   the heaviest. Benchmark averages are a shortlist, not a decision: STS and retrieval tasks are
   not CV–JD matching.
4. **Memory isn't the constraint**: all three fit in 512 MB with room for the API; potion is 2× lighter
   and 15× faster per match than MiniLM.
5. **No tuning on this proxy** (it includes the future test JDs). Ideas to test on **dev** only:
   down-weighting generic requirements, a hybrid of whole-document similarity and requirement
   coverage, and calibrating scores for display (K7 found the same issue).

## Next
- After J2 calibration and rating: `evaluate.py score` on dev for all six files plus TF-IDF; pick
  the model and mode in ADR-0004; run test once; record in the model card.
- S9 loads the chosen encoder once at startup (lifespan) and measures memory inside the real API.
