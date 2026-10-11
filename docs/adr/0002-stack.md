# ADR-0002: Stack and hosting for P1

**Status:** proposed · **Date:** 2026-10-09 · **Deciders:** Semanu, Kobi (accept at the kickoff sync)

## Context
P1 (Resume–Job Matcher) needs a public demo link by 2026-10-18. **Constraint: free tiers only.
We will not pay for hosting** (decided 2026-10-09). The template gives us a
FastAPI backend (Dockerfile with a `/health` smoke test in CI, port set by `PORT`) and a
React + Vite + TypeScript frontend that calls the API through `VITE_API_URL`. Neither of our laptops
runs Docker, so hosting must build the image for us. The repo will be public under the `kose-labs`
GitHub org, and both of us merge to `main` (squash merges, so the PR author is the commit author).

The original plan was a Hugging Face Docker Space for the backend and Vercel Hobby for the frontend.
Checking the providers' current docs (2026-10-09) changed that picture:

- **Hugging Face Docker Spaces now need a paid plan to create**: PRO ($9/month) for a personal
  account, Team ($20/user/month) for an organization. Our free `kose-labs` HF org cannot create one.
- **Vercel Hobby only deploys commits authored by the account owner.** Kobi's merged PRs would not
  auto-deploy from Semanu's account (or the reverse) through the Git integration.

## Free-tier limits (checked 2026-10-09)

| Provider | What's free | Limits that matter to us |
|---|---|---|
| **Vercel Hobby** (frontend) | Static sites, functions | Non-commercial personal use only. 100 GB transfer, 1M CDN requests, 100 deploys/day per month. Over a limit, the feature pauses for 30 days. Only the account owner's commits trigger Git deployments; deploying from GitHub Actions with the owner's token is the documented workaround. Private org repos are blocked on Hobby; public ones reportedly work. |
| **GitHub Pages** (frontend) | Static sites from the repo | 1 GB site, 100 GB/month soft bandwidth. Build limit doesn't apply when deploying with GitHub Actions. Not for commercial SaaS. No extra account; anyone who merges to `main` deploys. |
| **Hugging Face Docker Space** (backend) | CPU Basic hardware: 2 vCPU, 16 GB RAM, 50 GB disk (not persistent) | **Creating the Space needs PRO ($9/month) or Team.** Sleeps after a period without use. Container runs as UID 1000. Listens on 7860 unless `app_port` is set. Secrets arrive as env vars at runtime. Outbound traffic only on ports 80, 443, 8080. |
| **Render Free** (backend) | One web service from a Dockerfile | 512 MB RAM, 0.1 CPU. Sleeps after 15 min idle, about 1 minute to wake. 750 instance hours/month per workspace. No persistent disk; may restart at any time. Build minutes and bandwidth count against workspace allowances (amounts not published on the free-tier page). |
| Koyeb | No free compute any more (free Postgres only) | Not an option. |

## Options considered

**Stack**
1. **FastAPI + React/Vite/TypeScript (the template)**: both of us already run it natively, CI and
   the Docker smoke test are in place, and FastAPI gives OpenAPI docs for free. Cons: two apps to
   deploy instead of one.
2. **Single Python app (FastAPI serving the built frontend, or Gradio)**: one deployment. Cons:
   throws away the tested template and the frontend skills we want to show.

**Frontend hosting**
1. **GitHub Pages via GitHub Actions**: free, no new account, deploys whoever merges, works with a
   public org repo. Cons: static only (fine for a Vite build), no preview URLs per PR.
2. **Vercel Hobby**: preview URLs per PR, fast CDN. Cons: one owner; needs an Actions deploy with
   the owner's token for team commits; non-commercial only.

**Backend hosting**
1. **Render Free**: $0, builds our existing Dockerfile and sets `PORT` itself. Cons: 512 MB RAM
   rules out loading PyTorch-based models, and the 1-minute cold start makes a poor first impression
   for recruiters opening the demo.
2. **Hugging Face Docker Space (PRO $9/month, or Team $40/month for the org)**: 16 GB RAM.
   **Rejected: it costs money.**
3. **Hugging Face Gradio Space on ZeroGPU** (free for up to 2 Spaces on a personal account): could
   host only the model, called from the Render backend. Cons: a second service to run, a network hop
   on every request, GPU time quotas, and it lives on a personal account. Kept as a last resort.

## Decision (proposed)
- **Stack:** keep the template, FastAPI + React/Vite/TypeScript.
- **Frontend:** **GitHub Pages**, deployed by a GitHub Actions workflow on every merge to `main`.
- **Backend:** **Render Free**, from the existing Dockerfile. The model has to fit the 512 MB box:
  the TF-IDF baseline does easily, and for embeddings we use a lightweight runtime that avoids
  loading PyTorch (an ONNX-based library such as fastembed, or static embeddings such as model2vec).

## Consequences
- Zero cost, and no account-ownership traps: either of us can merge and deploy.
- **Memory is a hard requirement for the model.** ADR-0004 (model choice) must report peak memory
  of the running API and keep it well under 512 MB, measured with the same Docker image CI builds.
- Add a "waking up the server…" state to the frontend so a cold start doesn't look broken.
- `CORS_ORIGINS` on the backend must list the GitHub Pages URL; `VITE_API_URL` points at the backend.
- Revisit at the P1 retro (2026-10-18), or sooner if Render's limits bite.

## Sources
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby) ·
  [Commits not triggering deployments](https://vercel.com/kb/guide/commits-not-triggering-deployments) ·
  [Vercel for GitHub (Actions deploy)](https://vercel.com/docs/git/vercel-for-github) ·
  [Community: Hobby and org repos](https://community.vercel.com/t/why-cant-hobby-accounts-deploy-from-organizations/10015)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Hugging Face Spaces overview](https://huggingface.co/docs/hub/spaces-overview) ·
  [Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker) ·
  [Hugging Face pricing](https://huggingface.co/pricing)
- [Render free tier](https://render.com/docs/free) · [Render instance types](https://render.com/docs/compute-plans)
- [Koyeb pricing](https://www.koyeb.com/pricing)
