"""Test doubles for the match service."""

from app.schemas import MatchResponse, ModelInfo, Skills


class StubMatchService:
    """Returns a valid but empty result instantly, for tests that don't care about the score."""

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        return MatchResponse(
            score=0.0,
            skills=Skills(matched=[], missing=[]),
            evidence=[],
            model=ModelInfo(name="stub", version="0"),
            warnings=[],
        )
