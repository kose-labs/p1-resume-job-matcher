# K7: TF-IDF + cosine baseline

**Owner:** Kobi · **Date:** 2026-10-10 · **Code:** `backend/app/ml/tfidf.py`,
`backend/scripts/score_corpus.py` · **Data:** evaluation corpus (K5, [data card](../data_card.md))

## Hypothesis
TF-IDF vectors over word 1–2-grams, compared with cosine similarity, rank same-field CV–JD pairs
above unrelated ones well above chance, cheaply enough for Render Free (512 MB). It's the baseline
every later matcher (embeddings, K8) must beat on Spearman ρ.

## Setup
- **Corpus:** 30 JDs and 30 CVs, 5 each from Python, Data Science, JavaScript, Java, DevOps, QA:
  900 pairs.
- **Preprocessing:** `clean_text` and `tokenize` (K6). Stop words: scikit-learn's English list minus
  `go`, `r`, `c`, `net`, `rest`.
- **Vectorizer:** fitted **once on all 60 texts**, not per pair. `ngram_range=(1, 2)`, `min_df=1`,
  `sublinear_tf=True`.
- **Metric for now:** ROC AUC of "same field" vs "unrelated" and vs "nearby" pairs (Python ↔ Data
  Science, Java ↔ JavaScript, QA ↔ DevOps). **This is a proxy.** Field labels are self-chosen
  categories, not our ratings. The real metric, Spearman ρ against rated pairs, comes after J2.

## Results

| Variant | Vocabulary | Mean score (same / unrelated) | AUC same vs unrelated | AUC same vs nearby |
|---|---|---|---|---|
| **K7 default:** our tokenizer, 1–2-grams | 9,707 | 0.038 / 0.020 | **0.789** | **0.760** |
| Our tokenizer, unigrams only | 2,553 | 0.087 / 0.049 | 0.785 | 0.753 |
| Our tokenizer, 1–2-grams, `min_df=2` | 1,457 | 0.113 / 0.061 | 0.798 | 0.771 |
| scikit-learn's default tokenizer, 1–2-grams | 9,538 | 0.040 / 0.021 | 0.805 | 0.775 |

- **Memory:** peak RSS of the API process with scikit-learn imported, fitted and scoring all 900
  pairs: **132 MB** (41 MB without scikit-learn). Well inside the 400 MB target.
- **Speed:** fitting and scoring all 900 pairs takes well under a second.

## Conclusion
1. **The baseline works but is weak.** A random same-field pair outscores a random unrelated pair
   about 79% of the time. Nearby fields are almost as hard to separate (0.76).
2. **Raw scores are tiny** (0.02–0.04): long texts share few exact terms, and bigrams spread the
   weight thin. Spearman ρ only uses the ranking so this doesn't hurt the metric, but the API can't
   show 0.04 as "4% match". The score shown to users needs calibrating (K8/S9).
3. **No variant is clearly better on this proxy.** The gaps (≤ 0.02 AUC) are within the noise of
   150 same-field pairs from just 30 JDs. Our tokenizer exists for cases the field proxy can't see
   (a C# CV must not match a C++ job through the letter "c"; tested in `test_tfidf.py`).
4. **We don't tune on this proxy.** It uses all 30 JDs, including the 20 that become the test set,
   so choosing `min_df` or n-grams here would leak test information. Settings get chosen on the
   **dev** pairs once ratings exist, then frozen for the test run.

## Next
- J2: build the pair set and the calibration batch; then Spearman ρ on dev for these four variants.
- K8: sentence embeddings with chunking, compared on the same pairs and the same metric.
- Fitting for the API: one request has one CV and one JD, too few for IDF, so the deployed matcher
  is fitted at startup on a background corpus (S9).
