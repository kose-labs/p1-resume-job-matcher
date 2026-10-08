# KoSe Labs project template

Starting point for every KoSe Labs project: a **FastAPI** backend (Python) and a **React + TypeScript** frontend (Vite), with tests, linting, CI, Dependabot and secret scanning already wired up.

> **Using this template:** click **Use this template → Create a new repository**, then replace this README with `docs/project_plan.md`'s content and the project README template from the [handbook](https://github.com/kose-labs/handbook), and reset `CHANGELOG.md` to an empty `[Unreleased]` section. Keep `LICENSE` and `CONTRIBUTING.md`.

## Quickstart (no Docker needed)

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 24 LTS (pinned in `frontend/.nvmrc`).

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
npm ci
npm run dev
```
App on http://localhost:5173. It should say **"Backend connected"**; the Vite dev server forwards `/api` calls to the backend, so no CORS setup is needed locally.
`npm ci` installs exactly what `package-lock.json` lists; use `npm install <package>` only when adding a dependency.

**Once per clone**, after `uv sync` and `npm ci`, install the git hooks (Ruff, mypy, oxlint, Prettier, secret scanning, file hygiene):
```bash
uvx pre-commit install
```

### Windows notes
- Run the commands one per line. Windows PowerShell 5.1 doesn't support `&&`.
- If `npm` fails with *"running scripts is disabled on this system"*, call `npm.cmd` instead (for example `npm.cmd ci`), or allow local scripts for your account once:
  `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.
- If `npm ci` fails with `EPERM … unlink` inside `node_modules`, a program has a file there open, usually the Oxc VS Code extension or a running dev server. Close VS Code or stop the server, then run it again.

## Checks (the same ones CI runs)

| | Backend (`cd backend`) | Frontend (`cd frontend`) |
|---|---|---|
| Lint | `uv run ruff check .` | `npm run lint` |
| Format | `uv run ruff format --check .` | `npm run format:check` |
| Type check | `uv run mypy` | `npm run typecheck` |
| Tests | `uv run pytest` (includes coverage) | `npm test` |
| Coverage (80% minimum) | shown by `uv run pytest` | `npm run test:coverage` |
| Build | — | `npm run build` |

CI (`.github/workflows/ci.yml`) runs these on every pull request, plus:
- **pre-commit**: the hooks, including the **gitleaks** secret scan. It skips mypy, oxlint and Prettier because the backend and frontend jobs run those.
- **docker**: builds the backend image and checks that `/health` answers. This is how we test Docker without needing it on our laptops.

## Project structure

```
backend/
  app/            FastAPI app (routes, and later the ML package)
  tests/          pytest
  Dockerfile      image for CI and hosting
frontend/
  src/            React + TypeScript app
  .nvmrc          Node version, read by CI
docs/
  project_plan.md, adr/, model_card.md, data_card.md
.github/
  workflows/ci.yml, dependabot.yml, PR and issue templates
CHANGELOG.md      notable changes per version
CONTRIBUTING.md   branches, commits, reviews
LICENSE           MIT
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
