# Model Card: P1 Resume–Job Matcher

**Status:** draft, day 6 · results marked *pending* are filled in on day 8 from one test-set run per
model version · **Owner:** Kobi (ML lead) · **Reviewer:** Semanu

| | |
|---|---|
| **Served today** | `tfidf-baseline` 0.1.0: TF-IDF cosine similarity ([ADR-0006](adr/0006-production-tfidf.md)) |
| **Candidates** | Sentence embeddings with chunking (K8, [ADR-0004](adr/0004-embedding-model.md), proposed); a TF-IDF + embedding hybrid |
| **Skills** | `esco-dictionary` 0.2.0: ESCO v1.2 + tech dictionary, longest match (K9) |
| **Model chosen for V1** | *pending: ADR-0004, decided on dev ratings (day 7)* |

## What it does
Given one CV (text-based PDF) and one job description, the matcher returns:
- a **score** for how well the CV fits the job;
- the job's **skills** the CV covers and misses;
- **evidence:** the CV sentences that best answer the job's requirements (embeddings only).

## Intended use
- **A candidate** checks how a CV reads against a job they're considering and sees which listed
  skills the CV doesn't mention.
- **Comparing jobs for one CV.** Scores are more meaningful side by side than alone.
- **A portfolio demonstration** of an evaluated matching system.

## Out-of-scope use
- **Automated hiring decisions** (shortlisting, rejecting or ranking real applicants without a
  person reading the CV). The score measures written overlap with a job description, not ability.
- **Comparing different people** for the same job as a ranking of who is better.
- **Scanned CVs, DOCX, or languages other than English:** extraction fails or the vocabulary
  doesn't cover them.
- **Roles far from the evaluation fields** (Python, Data Science, JavaScript, Java, DevOps, QA).
  Nothing has been measured outside them.

## Models

### TF-IDF (served, baseline)
- **Fitted on** 3,000 public English Djinni job descriptions (MIT; 2020–2023), with the 30
  evaluation job descriptions excluded. No CVs, so no personal data is in the artefact.
- **Settings:** words and two-word phrases, `min_df=2`, up to 50,000 terms, sublinear TF, and our
  tokenizer, which keeps tech names whole ("C++", "Node.js", "CI/CD").
- **Artefact:** 238 KB gzipped JSON, byte-reproducible from `backend/scripts/build_tfidf_artifact.py`.

### Sentence embeddings (candidate)
- **Shortlist:** all-MiniLM-L6-v2, potion-base-8M, bge-small-en-v1.5 (ONNX, CPU).
- **Chunking:** job → requirement sentences (benefits and company text skipped, nice-to-haves at
  half weight), and CV → sentences, with long ones cut into 64-word windows. The score is the
  weighted mean of each requirement's best CV match. CVs are capped at 150 chunks (about 4 pages),
  and longer ones are flagged.

### Skill extraction
- **Dictionary first** (about 110 current tools, e.g. Docker, React, Kubernetes), then 944 ESCO
  skills with their alternative labels.
- **Precision rules:** ambiguous names ("Go", "Swift", "R") count only when written as names and
  in context, and ESCO's one-word generic synonyms are dropped.
- **Matched / missing:** a job skill is "matched" if the CV mentions it.

## Evaluation

### Data
- **120 CV–job pairs** from the [evaluation corpus](data_card.md): 30 job descriptions and 30 CVs,
  six fields.
- **Rated 1–5 by both of us,** independently, under the
  [annotation protocol](../research/annotation_protocol.md).
- **Split by job description:** dev is 10 JDs (40 pairs) and test is 20 JDs (80 pairs). Test is run
  once per model version.

### Rater agreement
Calibration batch (20 pairs): **quadratic weighted κ 0.785**, exact agreement 60%, within one point
95% (target κ ≥ 0.6). Main set: *pending*.

### Main metric: Spearman ρ against our ratings (test set)
Target: ρ ≥ 0.55, and ≥ 0.10 above TF-IDF. The 95% CIs come from a bootstrap that resamples job
descriptions.

| Model | ρ | 95% CI | Δρ vs TF-IDF | 95% CI |
|---|---|---|---|---|
| TF-IDF (served) | *pending* | | — | |
| *chosen model* | *pending* | | *pending* | |

### Field proxy (no ratings needed, all 900 pairs)
ROC AUC for telling same-field pairs from other pairs. This only checks the job field, not fit.

| Model | Same vs unrelated | Same vs nearby |
|---|---|---|
| TF-IDF, production artefact | 0.819 | 0.783 |
| TF-IDF, K7 baseline | 0.789 | 0.760 |
| MiniLM, whole document | 0.794 | 0.755 |
| MiniLM, chunked | 0.755 | 0.768 |

### Skill extraction (20 hand-labelled job descriptions)
Targets: F1 ≥ 0.70 and precision ≥ 0.80. Dev is 8 JDs and test 12, labelled by Kobi before seeing
the extractor's output. Results: *pending*.

### Serving
- **Latency:** `/api/v1/match` median 0.16 s (warm, 2-page CV, live). Target < 3 s.
- **Memory:** peak 192 MB with 4 concurrent 5 MB CVs (CI, 512 MB container). Target < 400 MB.

## Limitations and failure modes
- **The score isn't calibrated yet.** Raw TF-IDF similarity is small (median 0.043 for same-field
  pairs), so the page shows it with provisional bands, not as a percentage.
- **Written overlap, not ability.** A strong candidate with a short or unusual CV scores low. A CV
  that copies the job's wording scores high.
- **Small evaluation set:** 120 pairs, rated by two people who built the system. The CIs are wide,
  and the ratings reflect our judgement.
- **One data source:** Djinni posts from Ukraine's tech market, 2020–2023, English only.
- **Skills are only as good as the vocabulary.** A skill outside the dictionary and ESCO is never
  found, and an ambiguous name in an unusual sentence can still be missed or wrongly found.
- **Failure analysis:** the 10 pairs where the model and our ratings disagree most. *Pending
  (day 8).*

## Ethical considerations
- **Personal data:** CVs are processed in memory and never stored or logged. The served model
  contains no CV text. Evaluation CVs come from a public, MIT-licensed research dataset and stay
  out of the repository.
- **Bias:** the matcher sees only text. We ignore gender, age, nationality and English quality when
  rating, so the evaluation doesn't reward them. But a CV's wording can still reflect background,
  and the score inherits that.
- **Misuse:** the page and this card say the score is not a hiring decision, and the API is rate
  limited per visitor.

## Changes
| Version | Date | Change |
|---|---|---|
| draft | 2026-10-14 | Structure, models, proxy and serving numbers; rated results pending |
