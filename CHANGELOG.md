# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `evaluate.py compare` scores every model on the same rated pairs, with each model's gap to
  the deployed TF-IDF and a paired bootstrap CI for that gap, for the ADR-0004 decision.
- `evaluate.py gaps` lists the pairs where a model's rank and our rating disagree most (IDs only),
  for the model card's failure analysis.
- Test-set results, run once on the served model (`docs/evaluation.md`, model card, README): κ 0.734
  between us, Spearman ρ 0.553 (95% CI 0.394 to 0.707) for TF-IDF with no embedding model ahead,
  estimated-fit error 0.75 rating points, 51 of 80 pairs in the right band, skills precision 0.904
  and F1 0.715, and a failure analysis of the 10 largest gaps.
- Matches now list the job's skills in two groups: those the CV names (matched) and those it
  doesn't (missing), with ESCO links where they exist (K9 extractor, loaded once at startup).
- A rating page for J2 (`scripts/j2-pairs/rate.py`): one pair at a time, keys 1–5, notes, saved to
  the rater's sheet after every rating and resumable; never shows strata, splits or scores.
- Redesigned match page as a two-pane workspace: inputs on the left, a sticky results report on the
  right (one column on phones). Design tokens for colour, type, spacing and radius; light theme by
  default, a true-neutral dark theme and a manual theme toggle; IBM Plex Sans and Mono, self-hosted.
  The report shows the score in mono with a provisional band (Low / Moderate / Strong, from the
  deployed model's scores on our evaluation pairs), a flat meter, skills as matched / missing tags,
  evidence when available, and the model and round-trip time. Empty, loading (skeleton), success
  and error states, each error with a next step; Ctrl/Cmd + Enter runs a match. Subtle motion
  (the score bar draws in, the loading skeleton pulses, buttons press, theme changes fade), all off
  with reduced motion. Lighthouse accessibility 100, and no axe violations in any state or theme.
- "Use sample data" fills in a made-up job description and the fictional "Jordan Example" CV, so a
  visitor can try the matcher in seconds without a real CV (`frontend/public/sample-cv.pdf`).
- Model card draft (`docs/model_card.md`): intended and out-of-scope use, models, evaluation design,
  proxy and serving numbers, limitations and ethics; rated results to follow on day 8.
- The score reads as an **estimated fit from 0 to 100%**: how we'd likely rate the pair (rating 1 →
  0%, rating 5 → 100%), from a logistic curve fitted on our 40 dev ratings (`app.ml.calibration`,
  `evaluate.py calibrate`). It lands 0.76 rating points from our ratings on held-out JDs (1.08 for
  guessing the mean) and keeps the ranking, so ρ is unchanged. The band leads ("Strong fit") and the
  fit is rounded to 5% ("≈ 80%"), since its typical error is about ±19 points; the raw similarity
  stays visible. Bands sit on the shown fit (Low ≤ 40%, Moderate 45–55%, Strong ≥ 60%), so the band
  never contradicts the percentage; 27 of 40 dev pairs land in the right band, as before.
- Embedding matcher (`app.ml.embeddings`): JD requirements matched to CV sentences by cosine
  similarity, weighted mean of best matches, top pairs as evidence; model comparison in
  `docs/experiments/k8-embeddings.md` and ADR-0004 (proposed).
- Skill extraction (`app.ml.skills`, K9): ESCO v1.2 ICT, statistics, mathematics and digital
  skills (944, fetched from the ESCO API by `scripts/build_skills_vocab.py`) plus our tech
  dictionary, matched as whole tokens with the longest label winning; case-sensitive names (Go, R,
  Spring) and no generic one-word synonyms, for precision. `scripts/skill_eval.py` builds the
  labelling packet for 20 JDs and reports precision, recall and F1 (guide in
  `research/skill_labeling_guide.md`).
- Demo GIF in the README, recorded from the live site with the sample data
  (`scripts/demo/record_gif.py`).
- Opening the API's address (`/`) redirects to its interactive docs (`/docs`) instead of a 404.
- The API now scores with TF-IDF instead of the stub (S9, ADR-0006). The model is fitted on 3,000
  public Djinni job descriptions only (no CVs, evaluation set excluded) and shipped as a 238 KB
  gzipped-JSON artefact that `scripts/build_tfidf_artifact.py` rebuilds byte for byte. Scores are
  raw cosine similarities flagged `uncalibrated_score`, and the page explains it until they're
  calibrated against our ratings. `scripts/score_corpus.py --artifact` evaluates the production
  model.
- Serving (S9, ADR-0005): the match service loads once at startup (lifespan) and is injected with
  `Depends`; extraction and matching run in worker threads, at most `MATCH_CONCURRENCY` (2) at once,
  so `/health` stays fast during matches. CI now load-tests the Docker image at Render's 512 MB
  with four near-5 MB CVs and fails if peak memory passes 400 MB.
- CV text extraction from uploaded PDFs (ADR-0003): pdfplumber with a column split for two-column
  CVs, and clear 422 errors for password-protected or damaged files (`pdf_unreadable`), more than
  10 pages (`pdf_too_many_pages`) and scanned PDFs (`pdf_no_text`). Runs in a worker thread.
- Draft of Kobi's P1 build note (`docs/posts/p1-build-note-kobi.md`), for review before J3.
- Evaluation metrics in `app.ml.metrics` (quadratic weighted κ, tie-aware Spearman ρ), tested in CI
  against scikit-learn and SciPy reference values; `scripts/j2-pairs/evaluate.py` uses them.
- TF-IDF + cosine baseline matcher (`app.ml.tfidf`) and a script that scores every pair of the
  evaluation corpus (`scripts/score_corpus.py`); results in `docs/experiments/k7-tfidf-baseline.md`.
- Text preprocessing for CVs and job descriptions (`app.ml.preprocess`): cleanup of PDF and
  job-board artefacts (including pdfplumber's `(cid:N)` glyph placeholders), sections, sentences,
  and a tokenizer that keeps tech names such as C++, C#, .NET, Node.js and Go whole.
- `POST /api/v1/match` skeleton: request and response models from the API contract, a 5 MB CV
  limit enforced while the upload arrives (413), PDF check by file content (415) and field
  validation (422). Uploads stay in memory, never on disk. Returns a labelled stub result until the
  model lands.
- Frontend match form: job description and PDF upload with client-side checks, a "waking up the
  server" state for cold starts, loading and error states, and the score, skills and evidence.
- Frontend types generated from the backend's OpenAPI schema (`npm run api:schema`,
  `npm run api:types`); CI fails if the committed schema or types are out of date.
- Deployment: Render Blueprint for the backend (deploys after CI passes on `main`) and a GitHub
  Pages workflow for the frontend, with a deployment guide in `docs/deployment.md`.
- Rate limit on `POST /api/v1/match`: 10 requests a minute per client, answered with 429 and
  `Retry-After` before the upload is read.
- MIT license, contributing guide and this changelog.
- Docstrings on public backend functions, enforced by Ruff's `D1` rules (tests are exempt).
- Pre-commit hooks for mypy (backend), oxlint and Prettier (frontend), so type, lint and format problems are caught before pushing.
- Test coverage reports for backend (pytest-cov) and frontend (Vitest), shown in CI with an 80% minimum.

### Security
- Structured JSON logs with a request ID (also returned as `X-Request-ID`), method, path, status,
  duration, CV size, page count and outcome code, and nothing else: tests send marked CV and job
  description text and check it never reaches a log line. Uvicorn's access log, which records
  client IPs, is switched off.
- CI audits production dependencies for known vulnerabilities on every pull request:
  `pip-audit` on the backend's locked packages and `npm audit` (high and above) on the frontend's.
- The rate limit finds the client's IP by counting a configured number of trusted proxies
  (`TRUSTED_PROXY_HOPS`) from the right of `X-Forwarded-For`, instead of trusting every proxy with
  Uvicorn's `FORWARDED_ALLOW_IPS=*`, which let clients bypass the limit with a forged header.

### Changed
- ADR-0004 decided on our dev ratings (40 pairs, κ 0.770): TF-IDF stays the score (ρ 0.660); no
  embedding beats it by the 0.10 we required, so none ships in V1.
- ADR-0004 accepted by both of us on 2026-10-17. We drop the kickoff posts and post once, at the
  end of the project.
- Annotation protocol v2 (proposed for the J3 call): five rules from the calibration batch on
  seniority, overqualification, unwritten must-haves, CVs without technologies, and layout or English.
- An uncalibrated score is shown as a raw similarity with its provisional band ("0.043 Moderate"),
  not as a percentage, which read as a probability of fit.
- A match request still open after 60 s ends with a timeout message instead of spinning forever.
- Skill extraction 0.3.0: 48 tools and methods the extractor missed on the 8 dev JDs of our K9
  labels (SCSS, Webpack, EC2/ECS/EKS/RDS, TestRail, ELK, SDLC and more). On dev, F1 rises from
  0.687 to 0.886 at precision 0.966; the test JDs are measured once, after this change.
- Rating sheets are shared in `research/ratings/<rater>.csv` once both raters finish a batch; `evaluate.py` reads them from there (we still rate in the git-ignored `data/ratings/`).
- Score bands fitted to our dev ratings: Moderate from 0.04 and Strong from 0.055 (were 0.03 and
  0.06 from score quantiles), which put 27 of 40 rated pairs in the right band instead of 20.
- ADR-0001 (data sources) and ADR-0002 (stack and hosting) accepted by both of us on 2026-10-12.
- Project plan scope confirmed on day 9: TF-IDF ships, evidence moves to V1.1, fine-tuning (K10)
  stays out; one end-of-project post each replaces the kickoff, build-note and launch posts.
- `@types/node` is back on 24 to match Node 24 (a Dependabot update had raised it to 26).
- README quickstart uses `npm ci`, and adds Windows notes (PowerShell, script execution policy, locked files).
- Verified on Render that `TRUSTED_PROXY_HOPS=1` gives each visitor their own rate-limit budget and
  ignores forged `X-Forwarded-For` values; recorded in `docs/deployment.md` and `render.yaml`.
- Node is pinned to 24 LTS in `frontend/.nvmrc`; CI reads it from there. Dependabot no longer proposes major `@types/node` updates, which must match the Node version.

### Fixed
- Embedding matcher: a CV longer than 150 chunks (about 4 pages) is no longer cut silently. The
  result now says so (`cv_truncated`), ready for an API warning. Evidence shows each CV sentence once.
- Skill extraction (0.2.0) is more precise: a capitalised word at the start of a sentence ("Access
  to a laptop", "Express delivery") or a lone letter ("Series C") no longer counts as a skill unless
  it's in a list, next to another skill or named clearly elsewhere. React Native and Unix are their
  own skills, not React and Linux. Dictionary names now match in any casing ("Typescript", "MySql"),
  which ESCO's capitalised labels had made case-sensitive.
- "Computer science", "mathematics" and "statistics" next to a degree word ("BSc in Computer
  Science") are no longer listed as skills (extraction 0.3.1): the job asks for a degree there.
  Test precision 0.897 → 0.904, recall unchanged. In 0.3.2, words that only look like degrees
  ("MS Excel", "a major part", "master SQL", "university partners") no longer hide the field; it
  gives the same output on all 60 corpus documents, so the 0.3.1 numbers stand.
- The band scale no longer says "provisional".
- The result page no longer shows "None found" and "None" for skills when none were recognised in
  the job description (as now, before skill extraction lands); it says so in one line instead.
- On a phone, the job description box now leaves room for the rest of the form, so the CV picker
  and Run match are on the first screen (375×667: Run match ended 19px below the screen, now 21px
  above it). Tablets and desktops keep the taller box.
- Render deploy: the Dockerfile path and build context in `render.yaml` are now relative to the
  service's root directory (`backend/`), where Render resolves them. The first deploy failed looking
  for `backend/backend`.

## [0.1.0] - 2026-10-08

### Added
- FastAPI backend with `/health` and `/api/v1/version`, managed with uv.
- React + TypeScript frontend (Vite) that proxies `/api` to the backend in local development.
- CI for lint, format, type checks, tests, frontend build and a Docker `/health` smoke test.
- Pre-commit hooks (Ruff, gitleaks secret scan, file hygiene) and Dependabot.
- Pull request, issue and documentation templates.
