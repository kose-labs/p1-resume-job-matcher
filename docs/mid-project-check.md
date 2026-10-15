# Mid-project check (J3)

**Date:** 2026-10-13, day 5 of 10 · **For:** Kobi and Semanu, to agree on our call · **Status:** proposal

## Where we are against the plan

| Day | Milestone | Status |
|---|---|---|
| 1 | Plan, ADR-0001/0002, scaffold with CI, security baseline, kickoff posts | Done, except the kickoff posts: drafted, not yet published (J1) |
| 2 | Evaluation corpus (K5); PDF parser chosen (S6, ADR-0003) | Done; ADR-0003 still proposed |
| 3 | TF-IDF baseline (K7); `/api/v1/match` skeleton (S7) | Done |
| 4 | Embeddings (K8, ADR-0004); frontend form (S8) | Form done. Embeddings approved (#40), not merged; ADR-0004 waits for the dev ratings |
| 5 | Skill extraction with F1 (K9); model lifecycle and concurrency (S9) | S9 done (#44, #48). Extractor merged (#55); labels, F1 and wiring into the API pending |

Ahead of plan: the app is **live** (backend on Render, frontend on GitHub Pages, auto-deploy after
CI), with rate limiting, JSON logs without CV text, a dependency audit in CI, and a redesigned
interface (#56, in review).

**Behind plan: the ratings.** The calibration batch is done, but the main 100 pairs aren't rated,
so the main metric (Spearman ρ against our ratings) doesn't exist yet. Every model decision left
(ADR-0004, score calibration, skill weights) waits on it.

## Numbers so far

| What | Result | Target |
|---|---|---|
| Rater agreement, calibration batch (20 pairs) | weighted κ **0.785**, 95% within one point | κ ≥ 0.6 ✅ |
| Deployed TF-IDF, field proxy (900 pairs) | AUC **0.819** same vs unrelated, **0.783** same vs nearby (K7: 0.789 / 0.760) | reference only |
| Embeddings, field proxy (K8) | MiniLM 0.794 whole, 0.755 chunked; none beats TF-IDF | decided on ρ, not the proxy |
| Match score vs our ratings | **not measured yet** (needs the main set) | ρ ≥ 0.55 and ≥ 0.10 above TF-IDF |
| Skill extraction | **not measured yet** (needs Kobi's labels) | F1 ≥ 0.70, precision ≥ 0.80 |
| `/api/v1/match`, 2-page CV, warm | median **0.16 s** (live, synthetic CV) | < 3 s ✅ |
| Peak memory, 4 concurrent near-5 MB CVs | **192 MB** (CI, 512 MB container) | < 400 MB ✅ |
| `/health` during matches | median 100 ms from Ghana, incl. ~90 ms network; one reading 372 ms | < 200 ms: to confirm from Render's `duration_ms` logs |
| Frontend accessibility | Lighthouse **100**, no axe violations (#56) | — |

Two loose ends from these numbers: the plan says `/health` < 200 ms but `test_serving.py` checks
250 ms (pick one), and the per-visitor rate limit still needs the phone test in
`docs/deployment.md`.

## Risks, updated

| Risk | Now | Plan |
|---|---|---|
| Ratings not done in time, so no ρ | **High** | Both rate p021–p120 on day 6 (about 2 hours each), after agreeing protocol v2 |
| Embeddings don't beat TF-IDF | Medium (the proxy says so) | As ADR-0004 says: ship the better score, keep chunked embeddings for evidence, report both |
| Skill extraction precision | Medium | Fix sentence-initial capitals ("Access to …" → Microsoft Access) and read only requirement sections before wiring it in (review of #55) |
| Evidence repeats a CV sentence; long CVs capped at 150 chunks | Low | Dedupe for the UI; return a `cv_truncated` warning (review of #40) |
| Approvals dismissed whenever a branch is updated from `main` | Process | Update the branch, wait for CI, then approve and merge straight away |

## Proposed plan for days 6–10

| Day | Kobi (ML) | Semanu (engineering) |
|---|---|---|
| 6 (10-14) | Protocol v2; rate p021–p120; label the 20 skill JDs; merge #40 | Rate p021–p120; README and architecture docs; rate-limit phone test |
| 7 (10-15) | Dev evaluation: ρ for TF-IDF, MiniLM chunked/whole, hybrid (ADR-0004); skills P/R/F1 on dev; score bands from ratings | Wire skills (matched / missing) into `/api/v1/match`; precision fixes from the #55 review; memory check with the chosen model |
| 8 (10-16) | Test set once per model version; model card numbers; failure analysis (10 largest gaps) | Integrate the chosen model and evidence; calibrated score in the UI; frontend states for skills and evidence |
| 9 (10-17) | Data card and model card final; launch post draft | Security review; demo GIF; release candidate `v0.1.0-rc.1`; launch post draft |
| 10 (10-18) | Launch: check the Definition of Done below, publish posts | Launch: deploy, tag `v0.1.0`, CHANGELOG release section |

## Proposed Definition of Done (V1)
The plan says "Definition of Done met" on day 10 but never defines it. Proposal:

- [ ] Live: frontend on GitHub Pages and backend on Render, deployed from `main` with CI green.
- [ ] A visitor can run a match with the sample data in under 30 seconds and see a score, skills and evidence.
- [ ] Test-set results in the model card: ρ with a bootstrap CI for the shipped model **and** the TF-IDF baseline, skill P/R/F1, the failure analysis, and the known limits.
- [ ] Data card and ADRs up to date (each ADR accepted or explicitly superseded).
- [ ] README in our 14-section structure, with setup in five commands or fewer.
- [ ] Coverage at least 80% in CI (currently 99–100%); lint, types and the dependency audit pass.
- [ ] Privacy checks pass: no CV text in logs, uploads never touch disk, and the rate limit is verified per visitor.
- [ ] `CHANGELOG.md` has a `0.1.0` section and the release is tagged `v0.1.0`.
- [ ] Launch posts published by both of us.

## Decisions for the call
1. Accept ADR-0003 (PDF parser), ADR-0005 (serving) and ADR-0006 (production TF-IDF). ADR-0004 stays proposed until the dev ρ.
2. Protocol v2: talk through p003, then three questions from the calibration batch: cap a junior CV for a senior job at 3? How to rate a CV that names no technologies? A must-have that is probably there but not written?
3. Confirm the frozen scope (J1) and this Definition of Done.
4. The plan for days 6–10 above.
5. When each of us publishes the kickoff and build-note posts.
