# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
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
- The rate limit finds the client's IP by counting a configured number of trusted proxies
  (`TRUSTED_PROXY_HOPS`) from the right of `X-Forwarded-For`, instead of trusting every proxy with
  Uvicorn's `FORWARDED_ALLOW_IPS=*`, which let clients bypass the limit with a forged header.

### Changed
- `@types/node` is back on 24 to match Node 24 (a Dependabot update had raised it to 26).
- README quickstart uses `npm ci`, and adds Windows notes (PowerShell, script execution policy, locked files).
- Node is pinned to 24 LTS in `frontend/.nvmrc`; CI reads it from there. Dependabot no longer proposes major `@types/node` updates, which must match the Node version.

## [0.1.0] - 2026-10-08

### Added
- FastAPI backend with `/health` and `/api/v1/version`, managed with uv.
- React + TypeScript frontend (Vite) that proxies `/api` to the backend in local development.
- CI for lint, format, type checks, tests, frontend build and a Docker `/health` smoke test.
- Pre-commit hooks (Ruff, gitleaks secret scan, file hygiene) and Dependabot.
- Pull request, issue and documentation templates.
