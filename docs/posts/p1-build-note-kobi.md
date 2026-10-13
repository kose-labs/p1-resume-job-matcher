# P1 build note (Kobi, ML angle)

**Status:** draft, for Semanu to review · publish around the mid-project check (J3)
**Lesson:** the bigger model didn't win, and we only know because we measured.

---

**Build note from our Resume–Job Matcher: the bigger model didn't win (yet).**

Halfway through, the plan said embeddings would beat word counting. Our numbers say otherwise.

🧮 **The baseline is hard to beat.** TF-IDF, which scores a CV by the job's important words it
shares, separates same-field CV–job pairs from unrelated ones with an AUC of 0.79. A sentence-
embedding model (MiniLM) gets 0.79 too, at twice the memory. Splitting CVs into sentences, which
I expected to help, scored lower for every model I tried.

📏 **So the decision waits for real ratings.** That AUC is only a proxy: it checks job *fields*,
not fit. Semanu and I are rating 120 CV–job pairs from 1 to 5. On the first 20 we agreed well
(weighted κ 0.79, 95% within one point), and the one big gap taught us a rule: judge skills, not
how polished the English is.

🔎 **What ships is whatever ranks pairs the way we do.** If embeddings don't earn their memory,
they'll still explain the score: which CV line answers which requirement.

Next: rating the other 100 pairs, then the model choice.

*[visual: bar chart of AUC for TF-IDF, MiniLM whole and MiniLM chunked]*

---

**Word count:** about 190 (body only).

**Checks before publishing:**
- Numbers are from `docs/experiments/k7-tfidf-baseline.md` and `k8-embeddings.md` (TF-IDF 0.789,
  MiniLM whole 0.794, 247 MB vs 132 MB) and `evaluate.py agreement` (κ 0.785, 95% within one).
- "Twice the memory" compares peak RSS of the scoring runs (247 MB vs 132 MB); adjust if the
  deployed TF-IDF number (192 MB with the API) is the one quoted.
- Tag Semanu. No real CV or job description text in the visual.
