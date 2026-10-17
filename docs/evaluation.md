# Evaluation: P1 Resume–Job Matcher

**Test run:** 2026-10-17, once, on the served model · **Owner:** Kobi (ML lead) · **Reviewer:**
Semanu · Summary in the [model card](model_card.md)

## Summary
- **We agree with each other** well enough to judge the model: weighted κ 0.734 on the 80 test
  pairs (target ≥ 0.6).
- **The served TF-IDF score ranks pairs moderately like we do:** Spearman ρ **0.553** on test
  (95% CI 0.394 to 0.707). That meets the ρ ≥ 0.55 target, only just. Dev, where we chose the
  model, gave 0.660.
- **No embedding model beats it on test** either, so [ADR-0004](adr/0004-embedding-model.md)
  holds on data nobody tuned on.
- **Most of that ρ comes from telling fields apart.** Within same-field pairs it's 0.24: the score
  separates a Java CV from a QA job far better than it ranks two Java CVs for one Java job.
- **The estimated fit** lands 0.75 rating points from our ratings on test (1.04 for always guessing
  the dev mean), as on dev. **Bands** are right for 51 of 80 pairs, but only 2 of the 7 pairs we
  rated Strong come out Strong.
- **Skill extraction** meets both targets on test: precision 0.904, F1 0.715.

## Setup
- **Pairs:** 120 CV–job pairs from the [evaluation corpus](data_card.md) (30 Djinni job
  descriptions, 30 Djinni CVs, six fields). Each JD is in 4 pairs: 2 same-field, 1 nearby, 1
  unrelated.
- **Ratings:** both of us rated every pair 1–5, alone, under the
  [annotation protocol](../research/annotation_protocol.md), on a page that never shows the field,
  split or score. The target is the mean of our two ratings.
- **Split by JD:** dev is 10 JDs (40 pairs), test 20 JDs (80 pairs). Everything was chosen on dev:
  the model ([ADR-0004](adr/0004-embedding-model.md)), the score bands and the estimated-fit curve.
  Test was rated after those choices and run **once**; nothing was changed after seeing it.
- **Models:** the served TF-IDF artefact ([ADR-0006](adr/0006-production-tfidf.md)), the K7
  TF-IDF baseline and six embedding variants (K8), each scored once on the same pairs.
- **Uncertainty:** 95% intervals from 2,000 bootstrap rounds that resample JDs, since the 4 pairs
  of one JD aren't independent.

## Rater agreement

| Pairs | Weighted κ | Exact | Within one point |
|---|---|---|---|
| Calibration (20) | 0.785 | 60% | 95% |
| Dev (40) | 0.770 | 45% | 92% |
| **Test (80)** | **0.734** | 59% | 94% |
| All (120) | 0.758 | 54% | 93% |

Five test pairs differ by 2 points or more (p039, p047, p054, p102, p118). We didn't discuss or
change them: the target stays the mean of two independent ratings.

## Score: Spearman ρ against our ratings (test, 80 pairs, 20 JDs)
Target: ρ ≥ 0.55 for the served model. A model would replace TF-IDF only with ρ ≥ 0.55 **and**
Δρ ≥ 0.10 (ADR-0004); this is a check of that decision, not a new one.

| Model | ρ | 95% CI | Δρ vs served TF-IDF | 95% CI |
|---|---|---|---|---|
| **TF-IDF (served)** | **0.553** | 0.394 to 0.707 | — | |
| TF-IDF, K7 baseline | 0.535 | 0.357 to 0.698 | −0.018 | −0.070 to +0.023 |
| MiniLM-L6, whole | 0.529 | 0.379 to 0.666 | −0.023 | −0.229 to +0.169 |
| bge-small, whole | 0.512 | 0.331 to 0.654 | −0.040 | −0.248 to +0.153 |
| potion-base-8M, whole | 0.423 | 0.213 to 0.611 | −0.129 | −0.313 to +0.045 |
| MiniLM-L6, chunked | 0.295 | 0.051 to 0.528 | −0.258 | −0.453 to −0.048 |
| potion-base-8M, chunked | 0.285 | 0.025 to 0.528 | −0.268 | −0.482 to −0.056 |
| bge-small, chunked | 0.243 | −0.016 to 0.504 | −0.310 | −0.526 to −0.074 |

- **Dev to test:** TF-IDF fell from 0.660 to 0.553. Some drop is expected, because dev picked the
  model; the test intervals still overlap dev's.
- **Chunking hurts on test too,** clearly this time: all three chunked models are worse than
  TF-IDF with intervals below zero. Whole-text embeddings come close but don't beat it.

### Within each kind of pair

| Pairs | n | Mean rating | Median score | ρ within the group |
|---|---|---|---|---|
| Same field | 40 | 2.84 | 0.042 | 0.238 |
| Nearby field | 20 | 1.65 | 0.025 | 0.208 |
| Unrelated field | 20 | 1.10 | 0.019 | (almost all rated 1) |

The score is highest where we rate highest, which is most of the 0.553. Inside one field it barely
ranks candidates (0.24). For V1's intended use, comparing several jobs for one CV, telling fields
apart is the useful part; for comparing similar jobs in the same field, the score is weak.

## Estimated fit and bands (test)
The page turns the raw score into an estimated fit from 0 to 100% with a curve fitted on dev
(`evaluate.py calibrate`), shown to the nearest 5% with bands Low ≤ 40%, Moderate 45–55% and
Strong ≥ 60%.

- **Error:** 0.749 rating points on test, against 1.036 for always guessing the dev mean (dev,
  leaving one JD out: 0.762). About ±19 points on the 0–100% scale.
- **Bands:** 51 of 80 pairs (64%) in the band our mean rating gives (Strong ≥ 4, Low ≤ 2).
  Dev: 27 of 40 (68%). The raw thresholds the bands replace (0.04 / 0.055) also give 51.

| Our rating → / shown band ↓ | Low | Moderate | Strong |
|---|---|---|---|
| **Low** (50 pairs) | **41** | 6 | 3 |
| **Moderate** (23) | 6 | **8** | 9 |
| **Strong** (7) | 4 | 1 | **2** |

The page is reliable when it says a match is poor: 41 of the 50 pairs we rated Low are shown Low.
It's weak at recognising strong matches: 4 of the 7 we rated Strong are shown Low, and Strong is
shown for 14 pairs of which we'd rate only 2 Strong.

## Skill extraction (20 hand-labelled JDs; dev 8, test 12)
Targets: precision ≥ 0.80, F1 ≥ 0.70. Labels follow the
[labelling guide](../research/skill_labeling_guide.md) and were made before anyone saw the
extractor's output.

| Version | Split | Precision | Recall | F1 |
|---|---|---|---|---|
| 0.2.0 | dev | 0.948 | 0.538 | 0.687 |
| 0.3.0 | dev | 0.966 | 0.819 | 0.886 |
| 0.3.0 | test | 0.897 | 0.591 | 0.712 |
| 0.3.1 | dev | 0.972 | 0.819 | 0.889 |
| **0.3.1** | **test** | **0.904** | **0.591** | **0.715** |

- The test labels were checked twice: once for 0.3.0 and once for 0.3.1, whose degree rule came from
  the labelling guide and the dev misses, not from test errors.
- **0.3.2** (served) gives the same output as 0.3.1 on all 60 corpus documents, so these numbers
  apply to it without a third test run.
- Recall drops from dev to test (0.82 → 0.59) because 0.3.0 added the tools missed on dev. Test
  misses are mostly skills written as phrases ("testing web and mobile applications") rather than
  names.

## Failure analysis: the 10 largest gaps on test
Gap = the pair's rank by score minus its rank by our mean rating, on a 0–1 scale
(`evaluate.py gaps`). We read each pair in the rating packet; the texts stay out of the repository,
so this lists IDs and our reading of them.

| Pair | Kind | Our rating | Score | Gap | Why |
|---|---|---|---|---|---|
| p078 | same | 3.5 | 0.0127 | −0.75 too low | Short CV (≈ 830 characters) that names the right stack in other forms ("DRF" for Django REST Framework, FastAPI) and is mostly prose; the JD is half benefits |
| p067 | unrelated | 1.0 | 0.0609 | +0.73 too high | Generic CV (business applications, cross-functional teams, agile, delivering) meets a DevOps JD full of the same process words; no tech overlap |
| p033 | nearby | 1.0 | 0.0513 | +0.65 too high | Data-science CV and a scraping/engineering-manager JD share "data sources", "data" and "product"; the JD's Python, Scrapy and management needs aren't in the CV |
| p096 | same | 4.0 | 0.0204 | −0.64 too low | Very short CV (≈ 510 characters): six years of Java and microservices in plain prose; the JD is mostly company description |
| p092 | same | 1.5 | 0.0826 | +0.59 too high | Junior Linux/AWS support engineer against a senior Windows/Azure DevOps role: shared DevOps vocabulary (Git, deployment, infrastructure), wrong platform and seniority |
| p054 | nearby | 3.0 | 0.0172 | −0.56 too low | NLP researcher against a Python web role; **we disagree** (4 vs 2), so the target itself is uncertain |
| p052 | same | 2.0 | 0.0039 | −0.51 too low | Junior front-end CV vs an Angular tech lead: both of us rated it 2 and it's shown Low, so the band is right; the rank gap is large only because many pairs tie at 2 |
| p063 | nearby | 1.0 | 0.0382 | +0.51 too high | The same generic CV as p067, against a Java JD: process words again |
| p053 | same | 4.0 | 0.0302 | −0.46 too low | Java CV whose stack (Spring, JavaScript, Node.js) is in a short list inside long personal prose, which dilutes it |
| p046 | same | 2.0 | 0.0832 | +0.44 too high | Manual QA with 6 months' experience against a QA lead + Scrum Master role: same testing vocabulary, wrong level and role |

### Patterns
1. **Generic process words make poor matches look close** (p067, p063, p033). CVs written in
   general terms ("delivering solutions", "cross-functional", "agile") overlap with any JD that
   uses them, and TF-IDF can't tell those words from skills.
2. **Seniority and role level are invisible** (p092, p046, and p052 the other way). The protocol
   lowers a rating for a junior applying to a lead role; the score only sees shared field
   vocabulary.
3. **Short or prose-heavy CVs score too low** (p078, p096, p053). With few distinctive terms, or
   the stack buried in personal text, the cosine is small even when the experience fits.
   Abbreviations and alternative names ("DRF") don't match their full forms.
4. **Two gaps say more about the target than the model** (p054, where we disagree by 2 points, and
   p052, a tie at the bottom where the band is right).

### What would help (V2)
- **Seniority:** compare the years and level a JD asks for with the CV's (both are often stated).
- **Skill coverage in the score:** the share of the JD's skills the CV covers, combined with TF-IDF,
  would reward p078, p096 and p053 and penalise p067, p063 and p033. It must be chosen on dev and
  checked on a fresh test set, since this one has now been used.
- **Down-weighting boilerplate:** drop benefits and company sections and generic process words
  before scoring, as the chunked matcher already does for JDs.
- **Synonyms:** map common short forms ("DRF", "k8s") to their full names in the tokenizer.

## Limits of this evaluation
- **Small:** 80 test pairs from 20 JDs; the ρ interval is ±0.16.
- **Our judgement:** two raters who also built the system, rating Djinni posts from one market
  (Ukraine, 2020–2023, English).
- **Few strong pairs:** we rated only 7 test pairs Strong, so Strong-band accuracy rests on very
  few examples.
- **Test is now used:** further changes need a fresh test set, or must be reported as dev-only.

## Reproduce
From `scripts/j2-pairs/` (needs the corpus, `data/scores/` and both sheets in `research/ratings/`):

```bash
uv run python evaluate.py agreement
uv run python evaluate.py compare ../../data/scores/{tfidf-production,tfidf-baseline,minilm-l6-*,bge-small-*,potion-base-8m-*}.csv --split test
uv run python evaluate.py calibrate ../../data/scores/tfidf-production.csv --check test
uv run python evaluate.py gaps ../../data/scores/tfidf-production.csv --split test --top 10
```

Skills, from `backend/`: `uv run python -m scripts.skill_eval evaluate --split test`.
