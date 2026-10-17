# Annotation protocol v2: rating CV–job pairs

**Owner:** Kobi (K2) · **Status:** v2 proposed after the calibration batch, to agree on the
mid-project call (J3) · **Used by:** J2, and the P1 evaluation

Our main metric is **Spearman ρ between the matcher's scores and our ratings** of CV–JD pairs. The
metric is only as good as the ratings, so this document fixes how we rate. If you can rate a pair
using only this page, it works.

## The question you answer
> **"If I were the hiring manager for this job, how strongly would this CV make me want to
> interview the candidate?"**

Judge **fit for this job**, not CV quality. A brilliant CV for the wrong job is a 1. Rate from what's
written: don't guess skills the CV doesn't mention.

## The scale
Rate every pair with a whole number from **1 to 5**. Use 2 and 4 when a pair falls between the
anchors below.

| Rating | Meaning | Typical signs |
|---|---|---|
| **5** Strong fit | Would interview right away | Same role family. Covers most **must-have** requirements, including the main technology. Seniority about right (within ~2 years of the ask). |
| **4** | | Between 3 and 5: right role and main stack, but a notable must-have is missing or seniority is off by more. |
| **3** Partial fit | Might interview if the pool is thin | Related role or overlapping stack. About half of the must-haves are covered, or the main technology is missing but transferable (e.g. Java developer for a Kotlin job). |
| **2** | | Between 1 and 3: a few shared skills (e.g. both mention SQL or Git) but a different job. |
| **1** No fit | Would not interview | Different role family. Shared words are generic only (Agile, English, teamwork). |

### Anchor examples (synthetic)
These are made up for this page; real pairs come from the corpus.

**JD (Python backend developer):** *"3+ years of Python. Build REST APIs with FastAPI or Django.
PostgreSQL, Docker, CI/CD. Nice to have: AWS, Redis."*

- **5:** *"Python developer, 4 years. Built Django REST APIs for a fintech app; PostgreSQL schema
  design; Dockerized services deployed through GitLab CI. Some AWS (S3, ECS)."*
  Main stack, every must-have, seniority right.
- **3:** *"Data analyst, 3 years. Python (pandas, Jupyter) and SQL for reporting dashboards. Built a
  small Flask app for internal reports."*
  Python and SQL transfer, but no production API work, Docker or CI.
- **1:** *"Manual QA engineer, 5 years. Test cases, regression testing, Jira, Agile ceremonies,
  upper-intermediate English."*
  Different role family; only generic overlap.

## Rules
1. **Rate independently.** Don't discuss a pair with the other rater until both of you have
   submitted your ratings for the batch.
2. **Never look at the system's scores first.** Ratings are done before any model output is shown,
   and model scores are never in the rating sheet. Otherwise we measure how well we copy the model.
3. **Read the whole JD first**, mark its must-haves in your head (stated as required, "X+ years",
   or listed first), then read the CV.
4. **Don't use the dataset's category labels** (`Primary Keyword`) as a shortcut. They're hidden in
   the rating sheet.
5. **About one minute per pair.** If you're unsure after two minutes, pick the closest anchor and
   flag the pair in the `notes` column.
6. **No outside lookup.** Rate what's on the page.
7. **Ignore everything protected or irrelevant:** gender, age, nationality, photo-style details,
   writing style and English quality (unless the JD asks for an English level).

## Rules from the calibration batch (v2)
The calibration batch agreed well (weighted κ 0.785, 95% of pairs within one point), so the scale
stays as it is. These rules settle the cases where we disagreed (p003, p005, p013) or both wrote a
note (p009, p017). Apply them **after** placing the pair on the scale above.

8. **Seniority moves a rating by at most one point.** Within about 2 years of the ask: no change.
   A bigger gap, either way: −1. Exception: a CV with **no professional experience for a role that
   asks for 3+ years** is at most **3**, however well the skills match.
9. **Overqualified is not a penalty.** Six years for a junior role is rated on skills, like any
   other CV (p017).
10. **A must-have that isn't written is missing,** even when it is probably there. One exception:
    a skill **implied by a named tool** counts (Django or pandas imply Python, Spring implies Java,
    React implies JavaScript, Kubernetes implies containers). We rate the CV the matcher sees.
11. **A CV that names no technologies** is at most **2** for a technical job: we can't tell what
    the person can do (p005).
12. **Layout, length and English don't lower a rating** (rule 7). An unusual CV or imperfect
    English is rated on the skills and experience it shows, unless the JD asks for an English level
    (p003). If an unusual layout makes the content hard to find, read it twice before rating.

## The rating sheet
One CSV per rater. You rate in your working copy, `data/ratings/<rater>.csv` (git-ignored, like all
of `data/`):

```csv
pair_id,rating,notes
p001,4,
p002,1,
p003,3,"main stack missing, but strong Java"
```

The pair texts come from `data/pairs/pairs.jsonl`, built by script. The sheet only has `pair_id`,
so neither of us sees the other's ratings or any score.

**Sharing, only after a batch is finished by both of us** (calibration, then the main set): each of
us copies their sheet to `research/ratings/<rater>.csv` and commits it, and `evaluate.py` reads
from there. The sheet holds pair IDs, ratings and short notes only, so it is safe to commit:
**never quote CV or JD text in the notes.** Committing before the other has finished would let
them see your ratings, so wait until both say "done".

## Which pairs we rate (sampling plan)
The corpus (ADR-0001) has 30 JDs and 30 CVs, 5 each from six fields: Python, Data Science,
JavaScript, Java, DevOps and QA. All 900 pairs are too many to rate, so we sample **120 pairs**,
stratified so every rating level shows up:

| Stratum | Pairs | Expected ratings |
|---|---|---|
| Same field (e.g. Python JD × Python CV) | 60 | mostly 3–5 |
| Nearby field (Python ↔ Data Science, Java ↔ JavaScript, QA ↔ DevOps) | 30 | mostly 2–3 |
| Unrelated field | 30 | mostly 1–2 |

- Each JD appears in **4 pairs** (2 same-field, 1 nearby, 1 unrelated), so no single JD dominates.
- The sample is drawn by a script with a fixed seed and written to `data/pairs/pairs.jsonl`, then
  shuffled so strata aren't grouped together in the sheet.

## Calibration first (J2)
1. Both rate the same **20-pair calibration batch**.
2. Compute agreement: **quadratic weighted Cohen's κ**. Target **κ ≥ 0.6**.
3. Talk through every pair where we differ by 2 or more points, update this protocol (v2), then
   rate the remaining 100 pairs.
4. If κ < 0.6, add or sharpen anchor examples and rate a second calibration batch of 20.

## Final label and dev/test split
- **Final rating of a pair** = the mean of our two ratings (so 1, 1.5, 2, …, 5).
- **Split by JD, not by pair:** 10 JDs (and all their pairs) go to **dev**, 20 JDs to **test**, with
  each field represented in both. Splitting by pair would put the same JD in both sets and leak.
- We tune only on dev (TF-IDF settings, chunk size, score weights). **Test is used once per model
  version**, for the numbers in the model card.
- The calibration batch belongs to dev.

## Changes
| Version | Date | Change |
|---|---|---|
| v1 | 2026-10-10 | First version (K2) |
| v2 | 2026-10-13 | Rules 8–12 from the calibration batch (κ 0.785): seniority, overqualification, unwritten must-haves, CVs without technologies, layout and English |
