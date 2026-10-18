# P1 end-of-project post (Kobi, ML angle)

**Status:** draft for Kobi to rewrite in her own voice, then Semanu to review · publish on launch
day (2026-10-18), with the demo GIF · covers the launch post and the build note (one lesson with
evidence); the long-form write-up follows.

---

**We built a CV–job matcher, and the simplest model won.**

Paste a job description, drop in a CV, and it tells you how well they fit and which of the job's
skills the CV never mentions. Try it with the sample data in two clicks: [live link]

*[demo GIF: docs/screenshots/demo.gif]*

📏 **How we measured it.** Semanu and I rated 120 CV–job pairs from 1 to 5, separately (weighted κ
0.73 between us on the test pairs). We chose everything on 40 pairs and ran the other 80 once.

| On 80 held-out pairs | Spearman ρ vs our ratings |
|---|---|
| TF-IDF baseline | 0.535 |
| Best of 6 sentence-embedding variants | 0.529 |
| **TF-IDF, tuned and shipped** | **0.553** |

Skill extraction: 90% precision, F1 0.72 against hand labels.

🔎 **The lesson: word overlap isn't fit.** None of the embedding models did better than counting
shared words, so we shipped the one that fits in 200 MB. But most of that 0.55 comes from telling
fields apart. Among CVs and jobs from the *same* field, ρ drops to 0.24. The biggest misses: a
vague CV full of "cross-functional" and "agile" scored Strong for a DevOps job we both rated 1, and
a six-year Java developer with a five-line CV scored low for a Java job we rated 4. The page is good
at saying "poor match", and weak at spotting strong matches written in other words.

⚠️ **What it doesn't do:** judge ability, read scanned or non-English CVs, or see seniority. It's not
for hiring decisions.

**Next:** a seniority signal and skill coverage in the score, tested on fresh pairs.

🛠️ Python · FastAPI · scikit-learn TF-IDF · ESCO skills · React · Render + GitHub Pages
🔗 Demo · Repo · Model card

Data, evaluation and models: me. API, frontend, security and deployment: @Semanu Kwaku Sebuava 🙌

---

**Word count:** about 280 (body, without the table and links).

**Checks before publishing:**
- Every number is from `docs/evaluation.md` (test run 2026-10-17): κ 0.734; ρ 0.553 (CI 0.394 to
  0.707), K7 baseline 0.535, MiniLM-L6 whole 0.529; same-field ρ 0.238; skills precision 0.904,
  F1 0.715; the two examples are p067 (shown Strong, ≈ 65%) and p096 (Low, ≈ 20%) from the
  failure analysis.
- "Fits in 200 MB": peak 192 MB with 4 concurrent 5 MB CVs (CI memory check).
- "Did better": the embedding results are lower but their intervals overlap TF-IDF's; don't write
  "beat" or "far better".
- The GIF uses only the sample data and the fictional sample CV. No real CV or JD in any visual.
- Replace [live link], Demo, Repo and Model card with the real URLs; tag Semanu.
