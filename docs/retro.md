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
| Requirement-to-sentence evidence | Moved to V1.1 (#79); #78 stays a draft, so the evidence target wasn't measured |
| A calibrated percentage | An estimated fit from a curve fitted on dev, shown to 5% with bands (#80); 0.75 rating points of error on test |
| Kickoff and build-note posts | Dropped for one end-of-project post each (decided 2026-10-17) |
| Docker for local development | Native development; Docker only in CI and hosting |
| Live in 10 days | First live deploy on day 4 (2026-10-12, GitHub Pages + Render); `v0.2.0` released on day 10, 2026-10-18 |

**By the numbers (before the launch PR):** 58 merged PRs (Kobi 33, Semanu 24, Dependabot 1), 22
issues closed, 418 backend and 74 frontend tests at 100% coverage.

## Keep
*What worked and should carry into P2.*
- Kobi: deciding on dev and running test once. We rated blind, on a page that never showed the
  field, split or score (#66), and chose the model, bands and fit curve on 40 dev pairs, so the test
  numbers can be trusted, including the uncomfortable ones (same-field ρ 0.24, 2 of 7 Strong pairs
  shown Strong). Also, reading the worst pairs ourselves: the failure analysis gave us V2's first
  four issues (#88–#91).
- Semanu: reviewing by reproducing. Rerunning the numbers and the app before approving caught the
  band shown against the wrong percentage (#80) and the rollback that silently turns off auto-deploy
  (#85). Also, testing on the real host: only Render could prove the rate limit tells visitors apart.

## Stop
*What cost time or caused rework.*
- Kobi: leaving the evaluation data to the end. The test ratings (#81, #82) and the skill labels
  (#77) landed on day 9, so the test run, failure analysis, model card and launch design were all
  squeezed into the last two days. And opening many PRs at once that all edit the CHANGELOG: on
  days 7–9, four PRs (#60, #62–#64) needed re-approval only because the CHANGELOG had changed.
- Semanu: letting docs drift until launch. On release morning the README still said skills were
  "being evaluated" and three ADRs were "proposed" (#99, #100). And starting overlapping work late:
  we both began launch UI changes on day 9, and I stopped once Kobi took it.

## Try
*One or two changes for P2, each with an owner.*
- Kobi (owner): build the evaluation set first. Rate the pairs and label the skills by day 4,
  before comparing models, and include more strong pairs (we had only 7 of 80 on test), so
  Strong-band accuracy rests on more than a handful. And one CHANGELOG file per PR, combined at
  release, so parallel PRs stop conflicting.
- Semanu (owner): make docs move with the code. Add "README, ADRs and architecture updated?" to the
  PR template, and agree on the release numbers and tags on day 1 (we only found the untagged 0.1.0
  on launch day).

## V2 ideas (captured as issues)
From the failure analysis in [evaluation.md](evaluation.md) and what we cut from V1:
- #88 a seniority signal (years and level asked vs shown)
- #89 skill coverage combined with TF-IDF in the score
- #90 drop boilerplate and generic process words before scoring
- #91 synonyms for short forms (DRF, k8s)
- #92 one CV against several jobs, ranked
- #93 refit the fit curve on all 120 pairs and rate a fresh test set
- #47 guard PDF extraction against decompression bombs (from V1's security review)
