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
- Embedding matcher (`app.ml.embeddings`): JD requirements matched to CV sentences by cosine
  similarity, weighted mean of best matches, top pairs as evidence; model comparison in
  `docs/experiments/k8-embeddings.md` and ADR-0004 (proposed).
- Skill extraction (`app.ml.skills`, K9): ESCO v1.2 ICT, statistics, mathematics and digital
  skills (944, fetched from the ESCO API by `scripts/build_skills_vocab.py`) plus our tech
  dictionary, matched as whole tokens with the longest label winning; case-sensitive names (Go, R,
  Spring) and no generic one-word synonyms, for precision. `scripts/skill_eval.py` builds the
  labelling packet for 20 JDs and reports precision, recall and F1 (guide in
  `research/skill_labeling_guide.md`).
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
- Rating sheets are shared in `research/ratings/<rater>.csv` once both raters finish a batch; `evaluate.py` reads them from there (we still rate in the git-ignored `data/ratings/`).
- ADR-0001 (data sources) and ADR-0002 (stack and hosting) accepted by both of us on 2026-10-12.
- `@types/node` is back on 24 to match Node 24 (a Dependabot update had raised it to 26).
- README quickstart uses `npm ci`, and adds Windows notes (PowerShell, script execution policy, locked files).
- Node is pinned to 24 LTS in `frontend/.nvmrc`; CI reads it from there. Dependabot no longer proposes major `@types/node` updates, which must match the Node version.

### Fixed
- The result page no longer shows "None found" and "None" for skills when none were recognised in
  the job description (as now, before skill extraction lands); it says so in one line instead.
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
