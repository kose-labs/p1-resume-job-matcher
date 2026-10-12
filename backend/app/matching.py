"""The matching service the API calls: built once at startup, injected into each request."""

from typing import Protocol

from fastapi import Request

from app.schemas import MatchResponse, ModelInfo, Skills


class MatchService(Protocol):
    """Anything that can score a CV's text against a job description."""

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the match result for one CV and one job description."""
        ...


class StubMatchService:
    """Placeholder until the real pipeline lands (S9).

    Returns a valid but empty result, labelled `stub`, so the frontend can be built against the
    real contract before the model exists.
    """

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return an empty result that says it came from the stub."""
        return MatchResponse(
            score=0.0,
            skills=Skills(matched=[], missing=[]),
            evidence=[],
            model=ModelInfo(name="stub", version="0"),
            warnings=["stub_model"],
        )


def load_match_service() -> MatchService:
    """Build the matching service; called once at startup, never per request.

    The stub for now. Loading a real model (fitting TF-IDF, reading embedding weights) is slow,
    so it happens here, before the server accepts requests, not inside the first match.
    """
    return StubMatchService()


def get_match_service(request: Request) -> MatchService:
    """Provide the service loaded at startup (FastAPI dependency; tests override it)."""
    service: MatchService = request.app.state.match_service
    return service
