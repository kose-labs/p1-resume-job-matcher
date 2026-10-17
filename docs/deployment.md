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
| `TRUSTED_PROXY_HOPS` | Render (`render.yaml`) | `1`, then the number found below | How many proxies append to `X-Forwarded-For`. The rate limit takes the visitor's IP that many entries from the right; entries further left can be forged. |
| `MATCH_CONCURRENCY` | Not set (default) | `2` | Matches that may use the CPU at once (ADR-0005). CI's memory check confirms two near-5 MB CVs fit; lower to `1` if a heavier model doesn't. |
| `PORT` | Set by Render | `10000` | The Dockerfile already listens on `$PORT` on `0.0.0.0`. |
| `VITE_API_URL` | GitHub repo variable | The Render URL | Built into the frontend at build time. |

## Checking a deploy

1. `https://<service>.onrender.com/health` returns `{"status":"ok"}`. The first request after
   15 idle minutes takes about a minute while Render wakes the service.
2. The frontend shows **"Waking up the server…"**, then **"Server ready."**
3. A match with a synthetic test PDF returns a result. Never test the live site with a real CV.

## Reading the logs

The API writes one JSON line per request, plus one per match, to Render's **Logs** tab:

```json
{"time": "...", "level": "INFO", "event": "request", "request_id": "3f9c2a1b7d04", "method": "POST", "path": "/api/v1/match", "status": 200, "duration_ms": 412.5}
{"time": "...", "level": "INFO", "event": "match", "request_id": "3f9c2a1b7d04", "outcome": "ok", "cv_bytes": 48211, "pages": 2, "model": "tfidf-baseline"}
```

- Every response carries the same ID in an `X-Request-ID` header, so a user's report can be matched
  to its log lines by searching for the ID.
- `outcome` is `ok` or the error code (`pdf_no_text`, `pdf_unreadable`, `pdf_too_many_pages`).
- **No CV or job description text and no IP addresses are ever logged** (a test enforces the list of
  allowed fields). Uvicorn's own access log is off for the same reason (`--no-access-log`).

## Rate limit: finding the proxy count

Render puts several proxies in front of the app, and it keeps any `X-Forwarded-For` value the
visitor sends, adding its own entries after it. The visitor's real IP is therefore exactly as many
entries from the right as there are proxies; anything further left can be forged. Render doesn't
document the number of proxies, so find it once after the first deploy:

1. Start with `TRUSTED_PROXY_HOPS=1` (the Blueprint default).
2. **Separate visitors test:** use up the limit from your laptop (11 matches in a minute), then
   immediately try one match from your phone on mobile data. If the phone also gets
   "Too many requests", every visitor shares one budget: raise the value by 1 in Render
   (**Environment**), wait for the restart, and repeat.
3. **Forgery test:** at the value where the phone gets through, send 11 requests from the laptop,
   each with a different made-up `X-Forwarded-For` value, for example in PowerShell:

   ```powershell
   1..11 | ForEach-Object { curl.exe -s -o NUL -w "%{http_code}`n" -H "X-Forwarded-For: 10.0.0.$_" -F "cv=@test.pdf" -F "job_description=$('x' * 120)" https://<service>.onrender.com/api/v1/match }
   ```

   The 11th must print `429`. If all 11 succeed, the value is one too high: lower it by 1.
4. Record the final value in `render.yaml` with a pull request, so a rebuilt service keeps it.

Use a synthetic `test.pdf`, never a real CV.

**Result on Render (2026-10-15): `TRUSTED_PROXY_HOPS=1` is right.**
- *Forgery test:* with the laptop's budget used up, 11 requests with made-up `X-Forwarded-For`
  values all got `429`, so a forged header doesn't buy a fresh budget.
- *Separate visitors test:* the laptop was kept over the limit by a steady stream of requests
  (235 refused, about 10 a minute let through as slots freed). Meanwhile a phone on another network
  ran a match twice and got a result both times, so each visitor has their own budget.

Repeat both tests if Render changes its proxies or the service moves to another host.

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
| Everyone gets "Too many requests" | `TRUSTED_PROXY_HOPS` too low, so all visitors share a proxy's IP | Raise it as described in "Rate limit: finding the proxy count" |
| The rate limit never triggers | `TRUSTED_PROXY_HOPS` too high, so clients' forged addresses count | Lower it; rerun the forgery test |
| Backend restarts or answers 502 under load | Over Render Free's 512 MB | Check memory in Render's metrics; ADR-0002 and ADR-0004 set the memory budget for the model |
| Frontend loads but styles and scripts 404 | Wrong base path | The workflow builds with `--base=/<repo-name>/`; don't change it |
| Deploy frontend fails with "Set the VITE_API_URL repository variable" | Step 4 not done | Add the variable, re-run the workflow |
