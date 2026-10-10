# Deployment

Free tiers only (ADR-0002): the **frontend** is a static site on **GitHub Pages**, the **backend**
is the Docker image on **Render Free**.

| Part | Lives at | Deployed by | When |
|---|---|---|---|
| Frontend | `https://kose-labs.github.io/p1-resume-job-matcher/` | `.github/workflows/deploy-frontend.yml` | Every merge to `main` that touches `frontend/` |
| Backend | `https://<service>.onrender.com` (shown in Render) | Render, from `render.yaml` | Every merge to `main`, **after CI passes** (`autoDeployTrigger: checksPass`) |

## One-time setup

1. **GitHub Pages:** repo **Settings › Pages › Source: GitHub Actions**.
2. **Render account:** sign up at render.com with GitHub. When asked which repositories Render may
   access, allow `kose-labs/p1-resume-job-matcher` (an org owner has to approve this).
3. **Create the backend:** in Render, **New › Blueprint**, pick the repo, and apply. Render reads
   `render.yaml`: free plan, Frankfurt, `backend/Dockerfile`, health check on `/health`, and the
   environment variables below.
4. **Point the frontend at the backend:** copy the service URL from Render (for example
   `https://p1-resume-job-matcher-api.onrender.com`) into a repository **variable** (not a secret)
   named `VITE_API_URL`: **Settings › Secrets and variables › Actions › Variables**.
5. **First frontend deploy:** **Actions › Deploy frontend › Run workflow**, or merge any frontend
   change to `main`.

## Configuration

| Variable | Where | Value | Why |
|---|---|---|---|
| `CORS_ORIGINS` | Render (`render.yaml`) | `https://kose-labs.github.io` | Only our frontend may call the API from a browser. An origin has no path and no trailing slash. |
| `FORWARDED_ALLOW_IPS` | Render (`render.yaml`) | `*` | Requests reach the app through Render's proxy; this makes Uvicorn use each visitor's IP, so the rate limit is per visitor. |
| `PORT` | Set by Render | `10000` | The Dockerfile already listens on `$PORT` on `0.0.0.0`. |
| `VITE_API_URL` | GitHub repo variable | The Render URL | Built into the frontend at build time. |

## Checking a deploy

1. `https://<service>.onrender.com/health` returns `{"status":"ok"}`. The first request after
   15 idle minutes takes about a minute while Render wakes the service.
2. The frontend shows **"Waking up the server…"**, then **"Server ready."**
3. A match with a synthetic test PDF returns a result. Never test the live site with a real CV.

## Rolling back

- **Backend:** in Render, open the service's **Events**, pick the last good deploy and roll back to
  it. Then revert the bad change on `main` with a pull request, so the next deploy doesn't bring it
  back.
- **Frontend:** revert the change on `main` with a pull request; the workflow redeploys.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Stuck on "Waking up the server…" for over 2 minutes | Backend failed to start | Render service **Logs**; the build or the `/health` check failed |
| Every match says "Couldn't reach the server" | Wrong `VITE_API_URL`, or `CORS_ORIGINS` doesn't exactly match the Pages origin | Fix the variable, then re-run **Deploy frontend** / redeploy on Render |
| Everyone gets "Too many requests" | `FORWARDED_ALLOW_IPS` missing, so all visitors share the proxy's IP | Set it to `*` on Render |
| Backend restarts or answers 502 under load | Over Render Free's 512 MB | Check memory in Render's metrics; ADR-0002 and ADR-0004 set the memory budget for the model |
| Frontend loads but styles and scripts 404 | Wrong base path | The workflow builds with `--base=/<repo-name>/`; don't change it |
| Deploy frontend fails with "Set the VITE_API_URL repository variable" | Step 4 not done | Add the variable, re-run the workflow |
