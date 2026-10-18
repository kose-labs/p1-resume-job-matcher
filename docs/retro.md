# Retro: P1 Resume–Job Matcher

**Date:** 2026-10-18 (launch day) · **Who:** Kobi, Semanu · Format from the working agreement:
**keep / stop / try**, then V2 issues.

## What happened (facts from the repo)
Filled in from the plan, the PRs and the evaluation, so the discussion can start from the same
record.

| Planned (project plan, day 1) | What happened |
|---|---|
| Embeddings would beat TF-IDF by ρ ≥ 0.10 | No embedding met the rule on dev or test; TF-IDF shipped ([ADR-0004](adr/0004-embedding-model.md)) |
| ρ ≥ 0.55 for the shipped model | 0.553 on test (CI 0.39 to 0.71): met, only just; dev was 0.660 |
| κ ≥ 0.6 between us | 0.785 calibration, 0.770 dev, 0.734 test |
| Skills: precision ≥ 0.80, F1 ≥ 0.70 | 0.904 and 0.715 on test (0.3.1) |
| Requirement-to-sentence evidence | *[fill in: shipped in #78, or moved to V1.1]* |
| A calibrated percentage | An estimated fit from a curve fitted on dev, shown to 5% with bands (#80); 0.75 rating points of error on test |
| Kickoff and build-note posts | Dropped for one end-of-project post each (decided 2026-10-17) |
| Docker for local development | Native development; Docker only in CI and hosting |
| Live in 10 days | *[fill in on launch day]* |

**By the numbers:** *[fill in on launch day: merged PRs, issues closed, commits by each of us]*.

## Keep
*What worked and should carry into P2.*
- Kobi:
- Semanu:

## Stop
*What cost time or caused rework.*
- Kobi:
- Semanu:

## Try
*One or two changes for P2, each with an owner.*
- Kobi:
- Semanu:

## V2 ideas (captured as issues)
From the failure analysis in [evaluation.md](evaluation.md) and what we cut from V1:
- #88 a seniority signal (years and level asked vs shown)
- #89 skill coverage combined with TF-IDF in the score
- #90 drop boilerplate and generic process words before scoring
- #91 synonyms for short forms (DRF, k8s)
- #92 one CV against several jobs, ranked
- #93 refit the fit curve on all 120 pairs and rate a fresh test set
- #47 guard PDF extraction against decompression bombs (from V1's security review)
