from collections.abc import Sequence

import numpy as np
import pytest

from app.ml.embeddings import (
    WINDOW_WORDS,
    EmbeddingMatcher,
    Matrix,
    cv_sentences,
    jd_requirements,
    windows,
)
from app.ml.preprocess import tokenize


class BagOfWords:
    """Fake encoder: one dimension per word, so similar wording means similar vectors."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.calls = 0

    def encode(self, texts: Sequence[str]) -> Matrix:
        self.calls += 1
        rows = []
        for text in texts:
            row = np.zeros(500, dtype=np.float32)
            for token in tokenize(text):
                row[self.vocab.setdefault(token, len(self.vocab))] += 1
            rows.append(row)
        return np.array(rows)


JD = """We are a fintech startup building payment tools.
Requirements:
- 3+ years of Python backend development
- Experience with PostgreSQL databases
Nice to have:
- Kubernetes deployment experience
We offer:
- Remote work and a laptop budget
"""


def test_jd_requirements_skip_benefits_and_weigh_nice_to_have() -> None:
    reqs = jd_requirements(JD)
    texts = [r.text for r in reqs]
    assert "3+ years of Python backend development" in texts
    assert all("laptop" not in t for t in texts)
    weights = {r.text: r.weight for r in reqs}
    assert weights["Kubernetes deployment experience"] == 0.5
    assert weights["Experience with PostgreSQL databases"] == 1.0


def test_short_lines_are_not_requirements() -> None:
    assert jd_requirements("Requirements:\n- Python\n- Strong SQL query skills") == [
        r for r in jd_requirements("Requirements:\n- Strong SQL query skills")
    ]


@pytest.mark.parametrize("length", range(WINDOW_WORDS + 1, 301))
def test_long_sentences_become_overlapping_windows_without_losing_words(length: int) -> None:
    words = [f"w{i}" for i in range(length)]
    parts = windows(" ".join(words))
    assert len(parts) > 1
    assert all(len(p.split()) <= WINDOW_WORDS for p in parts)
    assert {w for p in parts for w in p.split()} == set(words)  # nothing dropped at the end


def test_short_sentences_stay_whole() -> None:
    sentence = " ".join(["word"] * WINDOW_WORDS)
    assert windows(sentence) == [sentence]


def test_cv_sentences_split_bullets() -> None:
    cv = (
        "Backend developer.\n- Built Python services for payments\n- Tuned PostgreSQL queries daily"
    )
    assert cv_sentences(cv) == [
        "Built Python services for payments",
        "Tuned PostgreSQL queries daily",
    ]


def test_matching_cv_scores_higher_and_evidence_points_at_the_right_sentence() -> None:
    matcher = EmbeddingMatcher(BagOfWords(), "fake")
    good = matcher.match(
        "- 4 years of Python backend development for banks\n"
        "- Designed PostgreSQL databases with experience in tuning",
        JD,
    )
    bad = matcher.match("- Manual QA testing of mobile games\n- Wrote test cases in Jira", JD)
    assert good.score > bad.score
    assert 0.0 <= bad.score <= good.score <= 1.0
    paired = {e.requirement: e.cv_excerpt for e in good.evidence}
    assert "Python" in paired["3+ years of Python backend development"]
    assert "PostgreSQL" in paired["Experience with PostgreSQL databases"]
    assert [e.similarity for e in good.evidence] == sorted(
        (e.similarity for e in good.evidence), reverse=True
    )


def test_nice_to_have_counts_half() -> None:
    matcher = EmbeddingMatcher(BagOfWords(), "fake")
    must = (
        "Requirements:\n- Experience with PostgreSQL databases\n- Kubernetes deployment experience"
    )
    nice = (
        "Requirements:\n- Experience with PostgreSQL databases\n"
        "Nice to have:\n- Kubernetes deployment experience"
    )
    cv = "- Experience with PostgreSQL databases at scale"
    assert matcher.match(cv, nice).score > matcher.match(cv, must).score


def test_empty_documents_score_zero_without_calling_the_model() -> None:
    encoder = BagOfWords()
    matcher = EmbeddingMatcher(encoder, "fake")
    assert matcher.match("", JD).score == 0.0
    assert (
        matcher.match("- Built Python services", "We offer:\n- Remote work for everyone").evidence
        == []
    )
    assert encoder.calls == 0


def test_evidence_size_is_capped() -> None:
    jd = "Requirements:\n" + "\n".join(f"- Skill number {i} with tools" for i in range(10))
    result = EmbeddingMatcher(BagOfWords(), "fake", evidence_size=3).match(
        "- Skill number 1 with tools", jd
    )
    assert len(result.evidence) == 3


@pytest.mark.parametrize("text", ["", "Hi", "Requirements:"])
def test_no_requirements_in_trivial_text(text: str) -> None:
    assert jd_requirements(text) == []
