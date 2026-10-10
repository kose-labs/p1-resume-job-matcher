# KoSe Labs project template

Starting point for every KoSe Labs project: a **FastAPI** backend (Python) and a **React + TypeScript** frontend (Vite), with tests, linting, CI, Dependabot and secret scanning already wired up.

> **Using this template:** click **Use this template → Create a new repository**, then replace this README with `docs/project_plan.md`'s content and the project README template from the [handbook](https://github.com/kose-labs/handbook).

## Quickstart (no Docker needed)

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22.

**Backend** (terminal 1):
```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```
API on http://localhost:8000, interactive docs on http://localhost:8000/docs.

**Frontend** (terminal 2):
```bash
cd frontend
npm install
npm run dev
```
App on http://localhost:5173. It should say **"Backend connected"**; the Vite dev server forwards `/api` calls to the backend, so no CORS setup is needed locally.

**Once per clone**, install the git hooks (ruff, secret scanning, file hygiene):
```bash
uvx pre-commit install
```

## Checks (the same ones CI runs)

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
|---|---|---|
| Lint | `uv run ruff check .` | `npm run lint` |
| Format | `uv run ruff format --check .` | `npm run format:check` |
| Type check | `uv run mypy` | `npm run typecheck` |
| Tests | `uv run pytest` | `npm test` |
| Build | — | `npm run build` |

CI (`.github/workflows/ci.yml`) runs these on every pull request, plus:
- **pre-commit**: all hooks, including the **gitleaks** secret scan.
- **docker**: builds the backend image and checks that `/health` answers. This is how we test Docker without needing it on our laptops.

## Project structure

```
backend/
  app/            FastAPI app (routes, and later the ML package)
  tests/          pytest
  Dockerfile      image for CI and hosting
frontend/
  src/            React + TypeScript app
docs/
  project_plan.md, adr/, model_card.md, data_card.md
.github/
  workflows/ci.yml, dependabot.yml, PR and issue templates
```

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`.
- `CORS_ORIGINS`: comma-separated frontend URLs allowed to call the deployed API.
- `VITE_API_URL`: the deployed backend URL for the production frontend build. Leave empty locally.

## Optional: Docker

If you have Docker: `docker compose up --build` runs the backend on port 8000. Not required for development.

## Rules that matter

- **No personal data in git.** CVs, datasets and anything in `data/` or `private-data/` are ignored. Only synthetic files go in `backend/tests/fixtures/`.
- **No secrets in git.** Hooks and GitHub push protection block them; still, check before you commit.
- **Every change goes through a pull request** with one review from the other person and green CI. See the [working agreement](https://github.com/kose-labs/handbook/blob/main/WORKING_AGREEMENT.md).

Built by [KoSe Labs](https://github.com/kose-labs).
