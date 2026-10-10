import pytest

from app.ml.tfidf import STOP_WORDS, TfidfMatcher

CORPUS = {
    "jd_python": "Python backend developer. Django, REST APIs, PostgreSQL and Docker.",
    "jd_qa": "Manual QA engineer. Test cases, regression testing, Jira, bug reports.",
    "jd_cpp": "C++ developer for embedded systems. Modern C++, Qt, Linux.",
    "cv_python": "Built Django REST APIs in Python with PostgreSQL, deployed with Docker.",
    "cv_qa": "QA engineer writing test cases, regression testing and bug reports in Jira.",
    "cv_csharp": "C# developer, .NET and ASP.NET Core web services.",
}


@pytest.fixture(scope="module")
def matcher() -> TfidfMatcher:
    return TfidfMatcher().fit(CORPUS.values())


def test_matching_pairs_score_higher_than_unrelated_ones(matcher: TfidfMatcher) -> None:
    same = matcher.score(CORPUS["cv_python"], CORPUS["jd_python"])
    other = matcher.score(CORPUS["cv_qa"], CORPUS["jd_python"])
    assert same > 0.2
    assert same > other


def test_scores_are_between_zero_and_one(matcher: TfidfMatcher) -> None:
    cvs = [CORPUS[k] for k in CORPUS if k.startswith("cv_")]
    jds = [CORPUS[k] for k in CORPUS if k.startswith("jd_")]
    scores = matcher.score_matrix(cvs, jds)
    assert scores.shape == (3, 3)
    assert (scores >= 0).all()
    assert (scores <= 1).all()


def test_identical_text_scores_one(matcher: TfidfMatcher) -> None:
    assert matcher.score(CORPUS["jd_qa"], CORPUS["jd_qa"]) == pytest.approx(1.0)


def test_csharp_cv_does_not_match_cpp_job_through_the_letter_c(matcher: TfidfMatcher) -> None:
    # With scikit-learn's default tokenizer both "C++" and "C#" become "c" (or vanish).
    assert matcher.score(CORPUS["cv_csharp"], CORPUS["jd_cpp"]) < 0.1


def test_shared_terms_explain_the_score(matcher: TfidfMatcher) -> None:
    terms = [t for t, _ in matcher.top_terms(CORPUS["cv_python"], CORPUS["jd_python"], k=5)]
    assert "django" in terms
    assert all(t not in STOP_WORDS for t in terms)


def test_bigrams_are_in_the_vocabulary(matcher: TfidfMatcher) -> None:
    assert "regression testing" in matcher.vectorizer.vocabulary_


def test_tech_names_are_not_stop_words() -> None:
    assert {"go", "r", "c"}.isdisjoint(STOP_WORDS)


def test_scoring_before_fit_fails() -> None:
    with pytest.raises(RuntimeError, match="fit"):
        TfidfMatcher().score("a", "b")
    with pytest.raises(RuntimeError, match="fit"):
        TfidfMatcher().top_terms("a", "b")
