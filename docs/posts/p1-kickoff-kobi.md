# P1 kickoff post (Kobi, ML angle)

**Status:** draft, for Semanu to review · publish after the kickoff sync

---

Semanu and I just kicked off the first KoSe Labs project: a **Resume–Job Matcher**. Paste a job
description, upload your CV, and it scores the fit, lists the required skills you cover and miss,
and shows the CV lines behind the score.

I'm leading the ML side, and the hard part isn't the model. It's knowing whether the score means
anything. So before writing any model code:

📏 **We built our own test set.** We each rate CV–job pairs from 1 to 5 on our own, check that we
agree, and only then compare the system's scores to ours.

📈 **Every model has to beat a simple baseline.** TF-IDF first, then sentence embeddings, judged
by how closely their scores rank pairs the way we do.

I'll share the numbers, including where it fails.

Shipping in 10 days. Follow along with @Semanu Kwaku Sebuava.

---

**Word count:** about 140 (body only). **Checks before publishing:** keep the metric wording the
same as Semanu's post ("how closely its scores agree with our ratings"); tag Semanu; attach the
architecture diagram or a screenshot of the form.
