"""The matching service the API calls, injected so it can be replaced in tests and in S9."""

from typing import Protocol

from app.schemas import MatchResponse, ModelInfo, Skills


class MatchService(Protocol):
    """Anything that can score a CV PDF against a job description."""

    def match(self, cv_pdf: bytes, job_description: str) -> MatchResponse:
        """Return the match result for one CV and one job description."""
        ...


class StubMatchService:
    """Placeholder until the real pipeline lands (S9).

    Returns a valid but empty result, labelled `stub`, so the frontend can be built against the
    real contract before the model exists.
    """

    def match(self, cv_pdf: bytes, job_description: str) -> MatchResponse:
        """Return an empty result that says it came from the stub."""
        return MatchResponse(
            score=0.0,
            skills=Skills(matched=[], missing=[]),
            evidence=[],
            model=ModelInfo(name="stub", version="0"),
            warnings=["stub_model"],
        )


def get_match_service() -> MatchService:
    """Provide the matching service to the endpoint (FastAPI dependency)."""
    return StubMatchService()
