"""The served model (S9, ADR-0006): TF-IDF loaded from the committed artefact."""

import gzip
import json

import pytest

from app.matching import TFIDF_ARTIFACT, TfidfMatchService, load_match_service
from app.ml.preprocess import clean_text, tokenize
from app.ml.tfidf import TfidfMatcher

CV = "Backend developer. Built REST APIs in Python with FastAPI and PostgreSQL, deployed on Docker."
JD_PYTHON = "Python backend engineer to build REST APIs with FastAPI, PostgreSQL and Docker."
JD_DESIGN = "Graphic designer for print and branding: Illustrator, InDesign, typography."


@pytest.fixture(scope="module")
def service() -> TfidfMatchService:
    return TfidfMatchService(TfidfMatcher.load(TFIDF_ARTIFACT))


def test_artefact_is_fitted_on_public_job_descriptions_only() -> None:
    meta = json.loads(gzip.decompress(TFIDF_ARTIFACT.read_bytes()))
    assert meta["source"]["dataset"] == "lang-uk/recruitment-dataset-job-descriptions-english"
    assert meta["source"]["licence"] == "MIT"
    assert meta["sample"]["documents"] == 3000
    assert meta["sample"]["excluded_evaluation_jds"] == 30
    assert len(meta["vocabulary"]) == len(meta["idf"]) == 50_000


def test_artefact_knows_tech_terms(service: TfidfMatchService) -> None:
    vocabulary = service.matcher.vectorizer.vocabulary_
    assert {"python", "c#", "c++", "node.js", "kubernetes", "rest api"} <= set(vocabulary)


def test_artefact_matches_the_current_tokenizer(service: TfidfMatchService) -> None:
    # The vocabulary was built with tokenize(). If tokenize() changes, CVs produce terms the
    # artefact doesn't know and scores quietly drop: rebuild the artefact (ADR-0006).
    terms = service.matcher.vectorizer.get_feature_names_out()
    stale = [term for term in terms if tokenize(clean_text(term)) != term.split(" ")]
    assert stale == [], f"rebuild with scripts/build_tfidf_artifact.py; e.g. {stale[:5]}"


def test_startup_serves_tfidf() -> None:
    assert isinstance(load_match_service(), TfidfMatchService)


def test_result_names_the_model_and_flags_the_score_as_uncalibrated(
    service: TfidfMatchService,
) -> None:
    result = service.match(CV, JD_PYTHON)
    assert result.model.name == "tfidf-baseline"
    assert result.warnings == ["uncalibrated_score"]
    assert 0 < result.score <= 1


def test_a_relevant_job_scores_higher_than_an_unrelated_one(service: TfidfMatchService) -> None:
    assert service.match(CV, JD_PYTHON).score > service.match(CV, JD_DESIGN).score


def test_no_shared_words_scores_zero(service: TfidfMatchService) -> None:
    assert service.match(CV, JD_DESIGN).score == 0
