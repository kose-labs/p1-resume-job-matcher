"""The matching service the API calls: built once at startup, injected into each request."""

from pathlib import Path
from typing import Protocol

from fastapi import Request

from app.ml.tfidf import TfidfMatcher
from app.schemas import MatchResponse, ModelInfo, Skills

# Fitted on public job descriptions only, rebuilt by scripts/build_tfidf_artifact.py (ADR-0006).
TFIDF_ARTIFACT = Path(__file__).parent / "ml" / "artifacts" / "tfidf-jds.json.gz"


class MatchService(Protocol):
    """Anything that can score a CV's text against a job description."""

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the match result for one CV and one job description."""
        ...


class TfidfMatchService:
    """Scores with the TF-IDF baseline (K7), fitted on public job descriptions only.

    Raw cosine scores are small until they're calibrated against our ratings (J2), so every result
    carries the `uncalibrated_score` warning. Skills and evidence arrive with K9 and K8.
    """

    def __init__(self, matcher: TfidfMatcher) -> None:
        """Wrap a fitted matcher."""
        self.matcher = matcher

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the TF-IDF cosine similarity of the CV and the job description."""
        return MatchResponse(
            score=round(self.matcher.score(cv_text, job_description), 4),
            skills=Skills(matched=[], missing=[]),
            evidence=[],
            model=ModelInfo(name=self.matcher.name, version=self.matcher.version),
            warnings=["uncalibrated_score"],
        )


def load_match_service() -> MatchService:
    """Build the matching service; called once at startup, never per request.

    Loading a model (reading the TF-IDF artefact now, embedding weights maybe later) happens here,
    before the server accepts requests, not inside the first match.
    """
    return TfidfMatchService(TfidfMatcher.load(TFIDF_ARTIFACT))


def get_match_service(request: Request) -> MatchService:
    """Provide the service loaded at startup (FastAPI dependency; tests override it)."""
    service: MatchService = request.app.state.match_service
    return service
