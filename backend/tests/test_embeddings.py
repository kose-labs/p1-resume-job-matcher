from collections.abc import Sequence

import numpy as np
import pytest

from app.ml.embeddings import (
    CV_CHUNK_LIMIT,
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
    cv = "\n".join(f"- Skill number {i} with tools" for i in range(10))
    result = EmbeddingMatcher(BagOfWords(), "fake", evidence_size=3).match(cv, jd)
    assert len(result.evidence) == 3


def test_evidence_shows_each_cv_sentence_once() -> None:
    # One CV sentence is the best match for every requirement: it's shown once, for the best one.
    jd = "Requirements:\n" + "\n".join(f"- Skill number {i} with tools" for i in range(5))
    result = EmbeddingMatcher(BagOfWords(), "fake").match("- Skill number 1 with tools", jd)
    assert [e.requirement for e in result.evidence] == ["Skill number 1 with tools"]


def test_long_cv_is_matched_on_its_first_chunks_and_flagged() -> None:
    matcher = EmbeddingMatcher(BagOfWords(), "fake")
    lines = [f"- Built service number {i} for clients" for i in range(CV_CHUNK_LIMIT)]
    assert not matcher.match("\n".join(lines), JD).cv_truncated
    longer = matcher.match("\n".join([*lines, "- Experience with PostgreSQL databases"]), JD)
    assert longer.cv_truncated
    # The sentence past the cap isn't used, so it can't be evidence.
    assert all("PostgreSQL" not in e.cv_excerpt for e in longer.evidence)
    assert len(cv_sentences("\n".join(lines * 2))) == CV_CHUNK_LIMIT


@pytest.mark.parametrize("text", ["", "Hi", "Requirements:"])
def test_no_requirements_in_trivial_text(text: str) -> None:
    assert jd_requirements(text) == []
