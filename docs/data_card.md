# Data Card: P1 evaluation corpus

**Status:** draft (K5) · **Built by:** [`scripts/k5-corpus/build_corpus.py`](../scripts/k5-corpus/build_corpus.py) · **Decision:** [ADR-0001](adr/0001-data-sources.md)

- **Source / link:** Djinni Recruitment Dataset, English parts:
  [job descriptions](https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english)
  (revision `b56a6054`) and
  [candidate profiles](https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english)
  (revision `86255174`). Paper: Drushchak and Romanyshyn,
  [*Introducing the Djinni Recruitment Dataset*](https://aclanthology.org/2024.unlp-1.2), UNLP @ LREC-COLING 2024.
- **Licence / terms of use:** MIT (both parts). The paper notes the data was provided by the Djinni
  platform for open research and commercial use. We cite the paper wherever we report results.
- **Size:** 30 job descriptions and 30 CVs (from 141,897 and 210,250), English only, 5 of each
  from six fields: Python, Data Science, JavaScript, Java, DevOps, QA. 900 possible CV–JD pairs.
- **Collected by / when:** Kobi, 2026-10-10, with the script above. Source posts and profiles date
  from 2020–2023.

## Contents
One JSON object per line in `data/corpus/jds.jsonl` and `data/corpus/cvs.jsonl` (synthetic example):

```json
{"id": "cv-python-01", "source_id": "50534b61-…", "field": "Python",
 "title": "Python/Django Developer", "text": "4 years of commercial Python…", "exp_years": "4.0"}
```

| Key | Meaning |
|---|---|
| `id` | Our stable ID: `jd-` or `cv-`, field, number |
| `source_id` | The record's ID in the Djinni dataset, so it can be traced back |
| `field` | Djinni's `Primary Keyword`. Used to sample pairs, **hidden from raters** |
| `title` | Job title / position the candidate is looking for |
| `text` | JD: the full posting. CV: Djinni's concatenated profile (highlights, experience, preferences) |
| `exp_years` | JD: years asked (e.g. `3y`). CV: years of experience |

Measured on this sample: JDs are 716 to 4,014 characters (median 1,597); CVs are 473 to 2,357
characters (median 1,130).

## Personal data
- **CVs are anonymized by the platform:** no names, e-mails, phones or links to profiles.
- **Second check:** the script replaces any e-mail, URL or phone number with `[EMAIL]`, `[URL]` or
  `[PHONE]` and records the counts in `manifest.json`. On this sample: **0 of each**.
- **Indirect identifiers remain:** employers, project descriptions and years can narrow someone
  down, and the paper (section 4) shows protected attributes such as gender can be inferred from
  the text. So the corpus is treated as personal data anyway: it stays in `data/` (git-ignored) on
  our machines, is rebuilt from the script, and is never published, uploaded to the demo or quoted
  at length in posts.

## Splits
Defined in the [annotation protocol](../research/annotation_protocol.md) and made when the pair set
is built (J2):
- 120 rated pairs out of 900: 60 same-field, 30 nearby-field, 30 unrelated; each JD in 4 pairs.
- **Split by JD:** 10 JDs (40 pairs, including the 20-pair calibration batch) for **dev**, 20 JDs
  (80 pairs) for **test**, each field in both. A JD never appears in both splits.
- The TF-IDF vectorizer is fitted on all 60 texts without labels (transductive, unsupervised).
  Settings are chosen on dev pairs only.

## Known biases & limitations
- **One market and period:** IT jobs in Ukraine, 2020–2023. Results may not hold for other
  countries, industries or newer job titles (e.g. "LLM engineer").
- **Profile-style CVs:** shorter and less structured than real PDF CVs (median ~1,100 characters vs
  a typical 3,000–6,000 for a two-page CV). Section headings are rare, so sectioning matters less here
  than on uploaded PDFs.
- **Text only:** the PDF extraction step isn't covered. It's tested separately (ADR-0003).
- **Six fields only,** all technical. Non-IT CVs are out of scope for V1.
- **Field labels are self-chosen** by candidates and recruiters (`Primary Keyword`), so they're a
  rough proxy for fit, never a label for evaluation.

## Preprocessing
- Sampling filters: English text; JDs 600–5,000 characters; CVs 400–5,000 characters.
- Order: MD5 of `id` + seed `kose-p1-k5`, first 5 per field. Same seed and revisions, same corpus:
  the output files' SHA-256 are in `manifest.json`.
- PII placeholders as above. No other change to the text: cleaning happens at match time in
  `backend/app/ml/preprocess.py` (K6), so the corpus stays the raw input the API would see.
