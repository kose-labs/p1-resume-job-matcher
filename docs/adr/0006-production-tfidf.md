# ADR-0006: Production TF-IDF fitted on public job descriptions, committed as a JSON artefact

**Status:** proposed · **Date:** 2026-10-12 · **Deciders:** Semanu (eng lead), Kobi (ML lead, review)

## Context
The deployed API needs a real matcher (S9). TF-IDF (K7, `app/ml/tfidf.py`) is the baseline, and
it needs IDF weights fitted **once on a corpus**: fitted on one CV and one job description, every
shared word looks equally rare and the score means nothing.

Constraints:
- CVs are personal data. ADR-0001 keeps the CV datasets on our machines, and in the #36 review we
  agreed that the production model is fitted on **public job descriptions only**.
- ADR-0001 also says nothing from the datasets is committed: the repo holds scripts and pinned
  revisions, and everyone regenerates the data.
- Render Free (ADR-0002) sleeps after 15 idle minutes, so the service starts often, on 0.1 CPU.
- The 30 job descriptions in the evaluation corpus must stay out of the fit, or the evaluation
  scores the model on text it has already seen.

## Options considered
1. **Fit at startup** from the Djinni parquet file. Rejected: a 139 MB download and a fit on every
   cold start, and the service can't start if Hugging Face is down.
2. **Fit per request** on the CV and job description. Rejected: IDF over two documents is
   meaningless (see above).
3. **Pickle the fitted scikit-learn vectorizer.** Rejected: loading a pickle can run arbitrary code,
   and the file breaks when scikit-learn's internals change.
4. **Include CVs in the fit.** Rejected: the vocabulary would contain words from people's CVs, in
   a public repository.
5. **Commit a JSON artefact built by a pinned, reproducible script** (chosen).

## Decision (proposed)
- **Corpus:** 3,000 English Djinni job descriptions of 600–5,000 characters
  (`lang-uk/recruitment-dataset-job-descriptions-english`, revision `b56a6054`, SHA-256 checked,
  MIT), picked by a seeded hash order (`kose-p1-tfidf`), with the 30 evaluation job descriptions
  excluded by reproducing the corpus script's selection.
- **Parameters:** words and two-word phrases, `min_df=2`, at most 50,000 terms, sublinear TF, our
  tokenizer and stop words (`app/ml/preprocess.py`, `app/ml/tfidf.py`).
- **Artefact:** `backend/app/ml/artifacts/tfidf-jds.json.gz` (238 KB): the vocabulary, the IDF
  weights and the provenance (dataset, revision, checksum, licence, citation, sample, parameters).
  Gzipped JSON without timestamps or file names, so the same inputs give a byte-identical file.
  Built by `backend/scripts/build_tfidf_artifact.py`.
- **A narrow exception to ADR-0001:** the artefact holds term statistics derived from public job
  posts, not their texts. Before committing, the vocabulary was checked for contact details: no
  email addresses or phone numbers; the only web addresses are company domains.
- **Serving:** `load_match_service()` loads the artefact at startup (about 150 ms, 8 MB). A missing
  or unreadable artefact stops the service from starting, so Render keeps the previous deploy.
- **The score is raw cosine similarity**, with the `uncalibrated_score` warning, and the page says
  it isn't calibrated. Raw TF-IDF scores for real pairs are small (0.02–0.04 in K7), so they can't
  be read as a percentage until they're calibrated against our ratings (J2, Kobi's decision).

## Consequences
- Rebuilding is one command from `backend/` (the first run downloads 139 MB into git-ignored
  `data/raw/`):
  ```
  uv run python -m scripts.build_tfidf_artifact
  ```
  Rebuild, and bump `TfidfMatcher.version`, whenever the tokenizer, stop words or parameters change.
  `tests/test_matching.py` fails if any term in the artefact no longer comes out of the current
  tokenizer unchanged, so a tokenizer change can't silently make CV terms unknown.
  A rebuild also moves the raw scores, so refit the estimated-fit curve afterwards
  (`scripts/j2-pairs/evaluate.py calibrate`) and update `FIT_CURVE` in
  `frontend/src/lib/scoreBands.ts`.
- The K7 numbers came from a vectorizer fitted on the evaluation corpus itself. The production fit
  differs, so the evaluation should be rerun with this artefact before quoting numbers for the
  deployed model (follow-up for K7/J2).
- The vocabulary comes from IT jobs on one job board: CVs and jobs outside IT share fewer known
  terms and score lower. The model card states this.
- Skills and evidence stay empty until K9 (skills) and K8 (embeddings) land; if the embedding model
  (ADR-0004) is adopted, it loads in `load_match_service()` next to or instead of TF-IDF.
