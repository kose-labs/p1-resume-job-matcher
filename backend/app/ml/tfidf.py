"""TF-IDF + cosine similarity: the baseline every later matcher has to beat (K7).

A document becomes a vector with one weight per word or two-word phrase: high when the term is
frequent in this document (TF) and rare across the corpus (IDF). Two documents match when their
vectors point the same way (cosine similarity, 0 to 1 for non-negative vectors).

The vectorizer is fitted **once on a whole corpus**, never per pair. IDF is a corpus statistic:
fitted on just one CV and one JD, every shared word would look equally rare and the weights would
mean nothing.
"""

import gzip
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Self

import numpy as np
import numpy.typing as npt
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from app.ml.preprocess import clean_text, tokenize

ARTIFACT_FORMAT = 1  # bump when the saved file's layout changes

# scikit-learn's English stop words, minus words that are also technology names.
STOP_WORDS = sorted(ENGLISH_STOP_WORDS - {"go", "r", "c", "net", "rest"})


class TfidfMatcher:
    """Score CVs against job descriptions with TF-IDF vectors and cosine similarity."""

    name = "tfidf-baseline"
    version = "0.1.0"

    def __init__(
        self,
        ngram_range: tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_features: int | None = None,
        vocabulary: Mapping[str, int] | None = None,
    ) -> None:
        """Configure the vectorizer; call `fit` before scoring (or use `load`)."""
        self.vectorizer = TfidfVectorizer(
            preprocessor=clean_text,
            tokenizer=tokenize,
            token_pattern=None,  # we tokenize ourselves; silences scikit-learn's warning
            lowercase=False,  # tokenize() already lowercases
            stop_words=STOP_WORDS,
            ngram_range=ngram_range,
            min_df=min_df,
            max_features=max_features,
            vocabulary=vocabulary,
            sublinear_tf=True,  # 1 + log(tf): ten mentions of "Java" aren't ten times the signal
        )
        self._fitted = False

    def save(self, path: Path, metadata: Mapping[str, Any]) -> None:
        """Write the fitted vocabulary and IDF weights as gzipped JSON, plus provenance metadata.

        JSON, not pickle: loading the file can't run code. `gzip.compress` with `mtime=0` leaves the
        time and the file name out of the gzip header, so the bytes depend only on the content and
        rebuilding from the same inputs gives an identical file.
        """
        if not self._fitted:
            raise RuntimeError("call fit() before saving")
        data = {
            "format": ARTIFACT_FORMAT,
            "name": self.name,
            "version": self.version,
            "ngram_range": list(self.vectorizer.ngram_range),
            **metadata,
            "vocabulary": self.vectorizer.get_feature_names_out().tolist(),
            "idf": [round(float(weight), 6) for weight in self.vectorizer.idf_],
        }
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path.write_bytes(gzip.compress(raw, mtime=0))

    @classmethod
    def load(cls, path: Path) -> "TfidfMatcher":
        """Rebuild a fitted matcher from a file written by `save`."""
        with gzip.open(path, "rb") as f:
            data = json.loads(f.read())
        if data.get("format") != ARTIFACT_FORMAT:
            raise ValueError(f"{path}: unsupported artefact format {data.get('format')!r}")
        vocabulary = {term: index for index, term in enumerate(data["vocabulary"])}
        matcher = cls(ngram_range=tuple(data["ngram_range"]), vocabulary=vocabulary)
        matcher.vectorizer.idf_ = np.asarray(data["idf"], dtype=np.float64)
        matcher.version = str(data["version"])
        matcher._fitted = True
        return matcher

    def fit(self, corpus: Iterable[str]) -> Self:
        """Learn the vocabulary and IDF weights from all CVs and JDs of the corpus."""
        self.vectorizer.fit(corpus)
        self._fitted = True
        return self

    def score_matrix(self, cvs: Sequence[str], jds: Sequence[str]) -> npt.NDArray[np.float64]:
        """Return a (len(cvs), len(jds)) array of cosine similarities in [0, 1]."""
        if not self._fitted:
            raise RuntimeError("call fit() on a corpus before scoring")
        # Rows are L2-normalized by the vectorizer, so the dot product is the cosine.
        cv_vectors = self.vectorizer.transform(cvs)
        jd_vectors = self.vectorizer.transform(jds)
        scores = np.asarray((cv_vectors @ jd_vectors.T).toarray(), dtype=np.float64)
        # Rounding can push identical documents a hair above 1.
        return np.clip(scores, 0.0, 1.0)

    def score(self, cv: str, jd: str) -> float:
        """Return the cosine similarity of one CV and one JD."""
        return float(self.score_matrix([cv], [jd])[0, 0])

    def top_terms(self, cv: str, jd: str, k: int = 10) -> list[tuple[str, float]]:
        """Return the k shared terms that add most to the score, for explaining it."""
        if not self._fitted:
            raise RuntimeError("call fit() on a corpus before scoring")
        cv_vec = self.vectorizer.transform([cv])
        jd_vec = self.vectorizer.transform([jd])
        contribution = cv_vec.multiply(jd_vec).toarray()[0]
        terms = self.vectorizer.get_feature_names_out()
        best = np.argsort(contribution)[::-1][:k]
        return [(str(terms[i]), float(contribution[i])) for i in best if contribution[i] > 0]
