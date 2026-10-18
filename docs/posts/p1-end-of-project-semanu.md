# P1 end-of-project post (Semanu, engineering angle)

**Status:** draft for Semanu to rewrite in his own voice, then Kobi to review · publish on launch
day (2026-10-18), with the demo GIF, alongside [Kobi's post](p1-end-of-project-kobi.md) · covers the
launch post and the build note (one lesson with evidence)

---

**We shipped a CV–job matcher on a free server with 512 MB of memory, and it never stores a CV.**

Paste a job description, drop in a CV, and it shows how well they fit and which of the job's skills
the CV never mentions. Two clicks with the sample data: [live link]

*[demo GIF: docs/screenshots/demo.gif]*

🔒 **Private by design.** The CV is read in memory and never saved: no database, no files, and a test
fails if CV or job text ever reaches a log line.

⚙️ **Built for a tiny server.** Render's free tier gives us 0.1 CPU and 512 MB. The model loads once at
startup, at most two matches run at a time, and four near-5 MB CVs at once peak at 192 MB. A warm
match comes back in under 0.2 s.

🧪 **The lesson: a passing test can still be wrong.** So I broke the code on purpose to prove each
test. Moving matching onto the server's main loop made the health check take 1.5 s instead of under
a quarter of a second, and the test failed, as it should. Some things only the real host can prove:
our rate limit has to tell visitors apart behind Render's proxies. I kept my laptop over the limit
(235 requests refused) while a phone on another network still got its results.

♿ Light and dark themes, full keyboard use, Lighthouse accessibility 100.

⚠️ **Limits:** text-based PDFs only (no scans), English, and the first match after a quiet spell
waits about a minute while the server wakes.

🛠️ FastAPI · pdfplumber · scikit-learn · React + TypeScript · GitHub Actions · Docker · Render +
GitHub Pages
🔗 Demo · Repo · Runbook

API, security, deployment and CI: me. Data, evaluation, models and the launch design: @Kobi Ampem
Afriyie, who also caught a rate-limit bypass in my code review 🙌

---

**Word count:** about 260 (body, without the links and the stack line).

**Checks before publishing:**
- **512 MB, 0.1 CPU:** Render Free ([ADR-0002](../adr/0002-stack.md),
  [ADR-0005](../adr/0005-serving.md)). **Load once, two at a time:** ADR-0005.
- **192 MB:** the CI memory check on `main` after the Dependabot merges (`314bbbe`, 2026-10-18):
  four 4.6 MB, 10-page CVs at once against the image capped at 512 MB.
- **Under 0.2 s:** three warm matches on the live API with the sample CV on 2026-10-18 took 0.13,
  0.17 and 0.19 s round trip.
- **Log test:** `backend/tests/test_logging.py` (allowed fields only, never CV or job text).
- **1.5 s vs under 0.25 s:** the mutation check on #44 (`tests/test_serving.py` keeps `/health`
  under 250 ms while four slow matches run).
- **235 refused, phone got through:** `docs/deployment.md`, "Result on Render (2026-10-15)".
- **Lighthouse 100:** re-measured on the launch design on 2026-10-18, desktop and mobile (#100).
- **About a minute to wake:** Render's free tier docs and our runbook (40–60 s measured).
- **Kobi's review:** the forged `X-Forwarded-For` bypass she caught on the rate-limit PR. She agreed
  to be named for it in the build note; check again before posting.
- The GIF uses only the sample data and the fictional sample CV. Replace [live link], Demo, Repo and
  Runbook with the real URLs, and tag Kobi.
