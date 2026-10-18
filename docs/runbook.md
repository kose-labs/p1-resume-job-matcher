# Runbook: P1 Resume–Job Matcher

**Owner:** Semanu (engineering lead) · **Backup:** Kobi · Setup and configuration details are in
[deployment.md](deployment.md); this page is what to do when the service is live.

## The service at a glance

| Part | Where | Deployed |
|---|---|---|
| Frontend | https://kose-labs.github.io/p1-resume-job-matcher/ (GitHub Pages) | On every merge to `main` that touches `frontend/` |
| API | https://p1-resume-job-matcher-api.onrender.com (Render Free, Frankfurt) | On every merge to `main`, after CI passes |
| Health | `GET /health` → `{"status":"ok"}` | Render checks it; CI smoke-tests the image |
| Version | `GET /api/v1/version` → `{"version":"0.2.0"}` | Shown in the page header |
| Logs | Render › service › **Logs** (one JSON line per request and per match) | Kept by Render, no CV or job text |

**Limits the users meet:** 10 matches per minute per visitor (`429` with `Retry-After`), CVs up to
5 MB and text-based PDFs only, job descriptions of 100–20,000 characters.

**Normal behaviour that looks like a fault:** after 15 idle minutes Render stops the service. The
next request wakes it in about 40–60 seconds; the page shows "Waking up the server…" meanwhile.

## Daily check (2 minutes)
1. Open the frontend. The header should reach **"Server ready"** (wait for the cold start).
2. Click **Use sample data**, then **Run match**. Expect a band, an estimated fit, skills and the
   model line (`tfidf-baseline 0.1.0`).
3. Glance at Render › **Logs** for `"level": "ERROR"` lines or a run of `5xx` statuses.
4. Glance at Render › **Metrics** › Application Metrics › memory: it should stay well under 512 MB (CI's load test peaks at
   about 192 MB).

Only ever test the live site with the sample CV or a synthetic PDF, never a real CV.

## Releasing a change
1. Open a PR; CI must pass (hooks, backend, frontend, Docker build + `/health` + memory check).
2. The other person approves; squash-merge.
3. Render deploys the API when the checks on `main` pass; the **Deploy frontend** workflow publishes
   the frontend. Watch both finish (Render › **Deploys**, GitHub › **Actions**).
4. Run the daily check above.
5. If the change touches the model, also follow "Model changes" below.

## Incidents

### The page is stuck on "Waking up the server…" (over 2 minutes)
1. `curl -s https://p1-resume-job-matcher-api.onrender.com/health`. If it answers `ok`, the API is
   fine: hard-refresh the page.
2. If not, Render › **Deploys**: did the last deploy fail? Render › **Logs**: did the app crash on
   startup (for example a missing artefact or an import error)?
3. Failed deploy → roll back, following all three steps in "Rolling back" (a rollback switches off
   auto-deploy). Crash loop on a deploy that used to work → check Render's status page, then
   redeploy the last good commit.

### Every match says "Couldn't reach the server"
- Usually configuration: `VITE_API_URL` (GitHub repo variable) or `CORS_ORIGINS` (`render.yaml`,
  exactly `https://kose-labs.github.io`, no path or trailing slash). See the troubleshooting table
  in [deployment.md](deployment.md#troubleshooting).
- In the browser's developer tools, a CORS error in the console confirms it.

### Many users get "Too many requests"
- One visitor at 10+ matches a minute is the limit working.
- Everyone at once means visitors share one budget: `TRUSTED_PROXY_HOPS` is wrong for Render's
  current proxies. Redo the two tests in
  [deployment.md](deployment.md#rate-limit-finding-the-proxy-count) and fix the value with a PR.

### 502s or restarts under load
- Render › **Metrics** › Application Metrics: memory near 512 MB means too many large CVs at once.
  Set `MATCH_CONCURRENCY=1` in Render › **Environment** (the default is 2) and redeploy; open an
  issue with the time and the request IDs.
- Then record the setting in `render.yaml` with a PR, as for `TRUSTED_PROXY_HOPS`, so a rebuilt
  service keeps it.

### A user reports a wrong or strange result
1. Ask for the **request ID**: it's in the `X-Request-ID` response header (browser developer tools ›
   Network). Search Render › **Logs** for it to see the outcome, page count and timing.
2. We never have the CV or job text, so we can't replay it. Ask the user for a synthetic example
   that shows the same problem, and never ask them to send a real CV.
3. Known limits (model card): generic wording scores too high, seniority is ignored, short CVs score
   too low, and a skill written as a phrase can be missed. If it's one of those, reply with the
   model card link; otherwise open an issue with the synthetic example.

### Privacy incident: CV or job text, or an IP address, appears in logs
This must never happen (a test enforces the allowed log fields).
1. Roll back to the last good deploy immediately ("Rolling back", all three steps).
2. Tell the other person; open a private note of what was logged, from when to when.
3. Render's logs can't be edited: if the exposure is real, contact Render support about deleting
   that log range, and record what you did.
4. Fix and add a test before redeploying.

### Abuse (scripted traffic, huge uploads)
- The rate limit, body-size limit and PDF checks absorb most of it. If it continues, suspend the
  service in Render (**Settings › Suspend**) and put a short notice on the frontend with a PR;
  resume when it stops.

## Rolling back
- **API:**
  1. Render › service › **Deploys** › the last good deploy › **Rollback** › **Rollback to this
     deploy**.
  2. Revert the bad commit on `main` with a PR, so the next deploy doesn't bring it back.
  3. **A rollback switches off auto-deploy** (Render's docs). Once the revert is merged and CI
     passes, turn auto-deploy back on in **Settings**, and check that the next deploy runs.
     Otherwise every later merge silently stays undeployed.
- **Frontend:** revert the commit on `main` with a PR; the workflow redeploys. To be faster, re-run
  an earlier successful **Deploy frontend** run from GitHub › **Actions**.

## Model changes
The served score is the TF-IDF artefact ([ADR-0006](adr/0006-production-tfidf.md)); skills come from
`app.ml.skills`; the estimated fit uses `FIT_CURVE` in `frontend/src/lib/scoreBands.ts`.
- **Rebuilding the artefact** moves the raw scores: refit the curve with
  `scripts/j2-pairs/evaluate.py calibrate`, update `FIT_CURVE`, and bump `TfidfMatcher.version`.
- **Any change that affects scores or skills** is evaluated on **dev** only. The test set was used
  for V1 on 2026-10-17 ([evaluation.md](evaluation.md)); a new test claim needs a fresh test set.
- Bump the **model version** (`TfidfMatcher.version`, or `SkillExtractor.version` for skills); the
  page shows the TF-IDF one as `tfidf-baseline 0.1.0`. Add a row to the model card's **Changes**
  table. The **app version** (`VERSION` in `app/main.py`, served at `/api/v1/version`) changes with
  a release, not with each model change.

## Routine maintenance
- **Dependabot** opens weekly PRs. Merge patch and minor updates when CI passes. Treat Python or
  Node major versions (for example the base image to Python 3.14) as their own change: build the
  image, run the memory check, and deploy on a quiet day.
- **Free tiers:** Render Free sleeps when idle and has monthly limits. When the workspace's 750 free
  instance hours or its bandwidth run out, Render **suspends all Free web services until the next
  month**, so check Render's usage page once a month. GitHub Pages and Actions are free for public
  repos.

## Contacts

| What | Who |
|---|---|
| API, hosting, deploys, rate limit | Semanu ([@Ohm-Kel](https://github.com/Ohm-Kel)) |
| Model, score, skills, evaluation | Kobi ([@Kobi-Ampem](https://github.com/Kobi-Ampem)) |
| Render or GitHub Pages outage | Their status pages; nothing to fix on our side but a notice |
