# P1 end-of-project post (Kobi, ML angle)

**Status:** ready for Kobi's final read, then publish on 2026-10-19 alongside
[Semanu's post](p1-end-of-project-semanu.md), with the demo GIF attached · covers the launch post
and the build note (one lesson with evidence); the long-form write-up follows.

---

**We built a CV–job matcher, and nothing beat the simplest model.**

Paste a job description, drop in a CV, and it tells you how well they fit and which of the job's
skills the CV never mentions. Try it with the sample data in two clicks:
https://kose-labs.github.io/p1-resume-job-matcher/

*[attach the demo GIF: docs/screenshots/demo.gif]*

📏 **How we measured it.** Semanu and I rated 120 CV–job pairs from 1 to 5, separately (weighted κ
0.73 between us on the test pairs). We chose everything on 40 pairs and ran the other 80 once.

| On 80 held-out pairs | Spearman ρ vs our ratings |
|---|---|
| TF-IDF baseline | 0.535 |
| Best of 6 sentence-embedding variants | 0.529 |
| **TF-IDF refitted on 3,000 job posts (shipped)** | **0.553** |

Skill extraction: 90% precision, F1 0.72 against hand labels.

🔎 **The lesson: word overlap isn't fit.** On the held-out pairs, none of the embedding models did
better than counting shared words, so we shipped the one that fits in 200 MB. But most of that 0.55
comes from telling fields apart. Among CVs and jobs from the *same* field, ρ drops to 0.24. The
biggest misses: a vague CV full of "cross-functional" and "agile" scored Strong for a DevOps job we
both rated 1, and a six-year Java developer with a five-line CV scored low for a Java job we rated
4. The page is good at saying "poor match", and weak at spotting strong matches written in other
words.

⚠️ **What it doesn't do:** judge ability, read scanned or non-English CVs, or see seniority. It's not
for hiring decisions.

**Next:** a seniority signal and skill coverage in the score, tested on fresh pairs.

🛠️ Python · FastAPI · scikit-learn TF-IDF · ESCO skills · React + TypeScript · Render + GitHub Pages

🔗 Demo: https://kose-labs.github.io/p1-resume-job-matcher/
🔗 Code: https://github.com/kose-labs/p1-resume-job-matcher
🔗 Model card: https://github.com/kose-labs/p1-resume-job-matcher/blob/main/docs/model_card.md

Data, evaluation, models and the launch design: me. API, security, deployment and CI: @Semanu Kwaku
Sebuava 🙌

---

**Word count:** about 290 (body, without the table and links).

**Checks before publishing:**
- Every number is from `docs/evaluation.md` (test run 2026-10-17): κ 0.734; ρ 0.553 (CI 0.394 to
  0.707), K7 baseline 0.535, MiniLM-L6 whole 0.529; same-field ρ 0.238; skills precision 0.904,
  F1 0.715; the two examples are p067 (shown Strong, ≈ 65%) and p096 (Low, ≈ 20%) from the
  failure analysis.
- **Semanu's review notes (#87), applied:**
  - "nothing beat the simplest model", not "the simplest model won": the gap to the best embedding
    is −0.023 with an interval from −0.23 to +0.17.
  - "Refitted on 3,000 job posts", not "tuned": the only difference from the baseline is the corpus
    it was fitted on ([ADR-0006](../adr/0006-production-tfidf.md)), and its +0.018 is within noise.
  - "On the held-out pairs": on dev, bge-small whole was +0.010.
- "Fits in 200 MB": peak 192 MB with 4 concurrent near-5 MB CVs (the CI memory check).
- The credits match Semanu's post and the README contributors.
- The GIF uses only the sample data and the fictional sample CV. No real CV or JD in any visual.
- The live link shows a preview card (#102); check it in LinkedIn's Post Inspector before posting.
- Tag Semanu, and link his post in a comment once both are up.
