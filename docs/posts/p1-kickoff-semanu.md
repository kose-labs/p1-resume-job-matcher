# P1 kickoff post (Semanu, engineering and security angle)

**Status:** draft, for Kobi to review · publish after the kickoff sync

---

Kobi and I just kicked off our first KoSe Labs project: a **Resume–Job Matcher**. Paste a job
description, upload a CV, and it shows how well they match, which required skills are covered or
missing, and the CV lines that back up the score.

I'm leading engineering and security. Two rules shape the build:

🔒 **Your CV is never stored.** It's processed in memory for one request, never written to disk or
logs, and scanned PDFs are rejected with a clear message rather than guessed at.

⚡ **It runs on free infrastructure.** The whole API has to fit in 512 MB of memory and answer in
under 3 seconds, so every model choice gets measured, not assumed.

The number we'll judge it by: how closely its scores agree with our own ratings of CV–job pairs.

Shipping in 10 days. Follow along with @Kobi Ampem Afriyie.

*[diagram: browser → GitHub Pages → FastAPI on Render → score, skills, evidence]*

---

**Word count:** about 150 (body only). **Checks before publishing:** the agreement metric is Kobi's
call (K1), so confirm the wording matches Kobi's target; tag Kobi; attach the architecture diagram from
the project plan.
