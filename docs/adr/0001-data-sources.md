# ADR-0001: Data sources for P1

**Status:** proposed · **Date:** 2026-10-10 · **Deciders:** Kobi, Semanu (accept at the kickoff sync)

## Context
The matcher has no training step at first (TF-IDF, then a pretrained embedding model), but we need
data for two things:

1. **An evaluation corpus** of about 30 job descriptions (JDs) and 30 CVs (K5), from which we build
   CV–JD pairs that we both rate 1–5 (annotation protocol, K2). Spearman ρ between our ratings and
   the system's scores is the main metric.
2. **End-to-end checks** of the real input path: CV as a PDF → text → match.

Constraints:
- **No personal data in git, ever** (working agreement). Data lives in `data/` (git-ignored) and is
  recreated by a script from public sources.
- **Licence must allow our use**, including a public repo and a public demo. Prefer permissive
  licences with clear provenance over scraped dumps with a licence added by the uploader.
- **English only** in V1 (plan, Out list).
- **Overlap between JDs and CVs.** If the CVs and JDs come from unrelated fields, every pair is an
  obvious non-match and the metric says nothing. We need related, partly related and unrelated pairs.

## Sources considered (checked 2026-10-10)

### Job descriptions
| Source | Licence | Size | Personal data | Notes |
|---|---|---|---|---|
| **Djinni Recruitment Dataset, English JDs** ([HF](https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english), [paper](https://aclanthology.org/2024.unlp-1.2/)) | MIT | 141,897 JDs, 2020–2023 | None expected (public job posts; company names kept) | Provided by the Djinni IT job platform, described in a peer-reviewed workshop paper (UNLP @ LREC-COLING 2024). Full posting text (median ~1,600 characters). `Primary Keyword` (Python, Java, DevOps, QA…) lets us sample by field. Ukrainian IT market. |
| Tech Job Postings, 9 ATS platforms ([HF](https://huggingface.co/datasets/makenomistakesllc/tech-job-postings-9-ats)) | CC BY 4.0 | 7,516 postings, Sep 2026 | None expected (public postings) | Recent full postings from 284 companies' career sites (Greenhouse, Lever, Workday…). Collected with a scraper, so the site terms sit behind the licence. Good for a small out-of-domain check. |
| Multi-ATS snapshot, NextGig ([HF](https://huggingface.co/datasets/NextGig-Rocks/global-job-postings-multi-ats)) | CC BY 4.0 | 112,816 | None expected | **Rejected:** `job_description` is a 2–4 sentence LLM summary, not the posting. We would be matching against generated text. |

### CVs
| Source | Licence | Size | Personal data | Notes |
|---|---|---|---|---|
| **Djinni Recruitment Dataset, English CVs** ([HF](https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english), same paper) | MIT | 210,250 profiles | Anonymized by the platform (no names or contacts). The paper (section 4) shows that protected attributes such as gender can still be inferred from the text. | Same market and years as the JDs, same `Primary Keyword` field, so related pairs exist. These are **profile-style CVs** (median ~750 characters), shorter and less structured than a PDF CV. Text only. |
| Kaggle Resume Dataset, snehaanbhawal ([Kaggle](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset), [HF mirror](https://huggingface.co/datasets/opensporks/resumes)) | CC0 as listed on Kaggle | 2,484 resumes in 24 categories, text + **PDF** | Example resumes from livecareer.com, names mostly removed | **The only one with PDFs**, which makes it useful for end-to-end checks of the upload path. But it was scraped from a resume-builder site and the CC0 label comes from the uploader, not the site, so we use it **locally only** and never redistribute or show it in the demo. Mostly non-IT categories. |
| ResumeAtlas ([HF](https://huggingface.co/datasets/ahmedheakl/resume-atlas), [paper](https://arxiv.org/abs/2406.18125)) | MIT | 13,389 resumes in 43 categories | Collected from public sources; contact details not guaranteed removed | Text only, built for category classification. Kept as a backup. |
| Our own CVs (Kobi, Semanu) | Our consent | 2 | **Yes** | Stored only in `private-data/` outside the repo. For demo sanity checks only, **not in the evaluation set**: we know them too well to rate them blind. |
| Synthetic CVs (Semanu's S6 fixtures) | Ours | 6 PDFs | None | Already used for the parser comparison and API tests. |

## Decision (proposed)
- **Evaluation corpus (K5): Djinni for both sides.** 30 English JDs and 30 English CVs, 5 of each
  from six fields: Python, Data Science, JavaScript, Java, DevOps, QA. That gives same-field pairs
  (likely matches), nearby-field pairs (Python ↔ Data Science, QA ↔ DevOps) and unrelated pairs.
  Sampling is deterministic (hash of the record ID with a fixed seed), from a pinned dataset
  revision, so anyone can rebuild the exact same corpus with one command.
- **End-to-end PDF checks:** a handful of IT-category PDFs from the Kaggle Resume Dataset, local
  only, plus Semanu's synthetic fixtures (the only PDFs that go into git).
- **Out-of-domain check (optional, after V1 metrics exist):** about 10 recent JDs from the 9-ATS
  dataset, credited as CC BY 4.0 requires.
- **Nothing from these datasets is committed.** The repo holds only the script, its pinned revisions
  and the record IDs it selected (`data/corpus/manifest.json` is regenerated, not committed).

## Consequences
- **Evaluation runs on text, not PDFs.** The PDF step is tested separately (ADR-0003 and the API
  tests). The model card must say the metric covers matching only.
- **Domain bias:** IT jobs in the Ukrainian market, 2020–2023, profile-style CVs. A good score here
  doesn't prove the matcher works for nursing or law CVs. Stated in the data and model cards.
- **Fairness:** protected attributes can leak through the text (paper, section 4). The matcher
  scores only skills and experience text, and we don't add any demographic features. Worth a
  research note, not a V1 fix.
- **Attribution:** cite the Djinni paper in the README and the model card; credit CC BY sources.
- Revisit if the Spearman numbers look too easy (corpus too separable) or when we add
  non-IT fields in V2.
