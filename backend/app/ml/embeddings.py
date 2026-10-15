"""Sentence-embedding matcher with chunking (K8).

TF-IDF only sees shared words. Embeddings place sentences with similar meaning close together, so
"built REST services in FastAPI" can match "experience developing APIs in Python".

Embedding a whole CV as one vector would blur it: a two-page CV becomes an average of everything
in it, and models silently cut text past their token limit. So both documents are **chunked**:

- the job description into **requirements**: sentences from its requirements / responsibilities /
  nice-to-have sections (benefits and company blurbs are skipped);
- the CV into **sentences**, with long ones cut into overlapping windows so nothing is truncated.

Each requirement is then matched to its most similar CV sentence (max similarity), and the score is
the weighted mean of those best matches: "how well is each requirement covered, on average?". The
best-matched pairs double as the **evidence** the API returns.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt

from app.ml.preprocess import clean_text, split_sections, split_sentences

Matrix = npt.NDArray[np.float32]

# Section weights for job descriptions; sections not listed (e.g. "experience") weigh 1.0.
SECTION_WEIGHTS = {"nice_to_have": 0.5}
SKIPPED_SECTIONS = {"benefits", "company"}
MIN_WORDS = 3  # shorter lines ("Requirements", "Kyiv, remote") carry no requirement
WINDOW_WORDS = 64  # well inside every shortlisted model's token limit
WINDOW_STRIDE = 48  # 16 words of overlap, so a phrase cut at a boundary appears whole once


class Encoder(Protocol):
    """Anything that turns texts into one embedding row each."""

    def encode(self, texts: Sequence[str]) -> Matrix:
        """Return a (len(texts), dim) array of embeddings."""
        ...


@dataclass(frozen=True)
class Requirement:
    """One sentence of a job description and how much it counts."""

    text: str
    weight: float


@dataclass(frozen=True)
class Evidence:
    """A requirement, the CV sentence that best covers it, and their similarity."""

    requirement: str
    cv_excerpt: str
    similarity: float


@dataclass(frozen=True)
class MatchResult:
    """Score in [0, 1] and the strongest requirement–sentence pairs, best first."""

    score: float
    evidence: list[Evidence]


def windows(sentence: str) -> list[str]:
    """Cut a long sentence into overlapping word windows; short ones stay whole."""
    words = sentence.split()
    if len(words) <= WINDOW_WORDS:
        return [sentence]
    # The last window starts early enough to end on the last word.
    starts = range(0, len(words) - WINDOW_WORDS + WINDOW_STRIDE, WINDOW_STRIDE)
    return [" ".join(words[i : i + WINDOW_WORDS]) for i in starts]


def _chunks(text: str) -> list[str]:
    return [w for s in split_sentences(text) if len(s.split()) >= MIN_WORDS for w in windows(s)]


def jd_requirements(text: str, limit: int = 40) -> list[Requirement]:
    """Return the job description's requirement sentences with their weights."""
    requirements = [
        Requirement(chunk, SECTION_WEIGHTS.get(section.name, 1.0))
        for section in split_sections(clean_text(text))
        if section.name not in SKIPPED_SECTIONS
        for chunk in _chunks(section.text)
    ]
    return requirements[:limit]


def cv_sentences(text: str, limit: int = 150) -> list[str]:
    """Return the CV's sentences (and windows of long ones)."""
    return _chunks(clean_text(text))[:limit]


def _normalize(m: Matrix) -> Matrix:
    m = np.asarray(m, dtype=np.float32)
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return (m / np.where(norms == 0, 1, norms)).astype(np.float32)


class EmbeddingMatcher:
    """Score a CV against a job description by matching requirements to CV sentences."""

    version = "0.1.0"

    def __init__(self, encoder: Encoder, name: str, evidence_size: int = 5) -> None:
        """Wrap an encoder; `name` identifies the model in results (e.g. "bge-small")."""
        self.encoder = encoder
        self.name = name
        self.evidence_size = evidence_size

    def match(self, cv: str, jd: str) -> MatchResult:
        """Return the weighted mean best-match similarity and the top evidence pairs."""
        requirements, sentences = jd_requirements(jd), cv_sentences(cv)
        if not requirements or not sentences:
            return MatchResult(0.0, [])
        req_vecs = _normalize(self.encoder.encode([r.text for r in requirements]))
        cv_vecs = _normalize(self.encoder.encode(sentences))
        similarity = req_vecs @ cv_vecs.T  # cosine, since rows are unit length
        best = np.clip(similarity.max(axis=1), 0.0, 1.0)
        where = similarity.argmax(axis=1)
        weights = np.array([r.weight for r in requirements])
        score = float(best @ weights / weights.sum())
        top = np.argsort(-best)[: self.evidence_size]
        evidence = [
            Evidence(requirements[i].text, sentences[where[i]], round(float(best[i]), 4))
            for i in top
        ]
        return MatchResult(round(score, 4), evidence)
