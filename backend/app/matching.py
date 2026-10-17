"""The matching service the API calls: built once at startup, injected into each request."""

from pathlib import Path
from typing import Protocol

from fastapi import Request

from app.ml.skills import SkillExtractor
from app.ml.tfidf import TfidfMatcher
from app.schemas import MatchResponse, ModelInfo, Skill, Skills

# Fitted on public job descriptions only, rebuilt by scripts/build_tfidf_artifact.py (ADR-0006).
TFIDF_ARTIFACT = Path(__file__).parent / "ml" / "artifacts" / "tfidf-jds.json.gz"


class MatchService(Protocol):
    """Anything that can score a CV's text against a job description."""

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the match result for one CV and one job description."""
        ...


class TfidfMatchService:
    """Scores with the TF-IDF baseline (K7), fitted on public job descriptions only, and splits the
    job's skills (K9) into those the CV mentions and those it doesn't.

    Raw cosine scores are small until they're calibrated against our ratings (J2), so every result
    carries the `uncalibrated_score` warning. Evidence arrives with the embedding matcher (K8).
    """

    def __init__(self, matcher: TfidfMatcher, skills: SkillExtractor) -> None:
        """Wrap a fitted matcher and a loaded skill extractor."""
        self.matcher = matcher
        self.skills = skills

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the TF-IDF cosine similarity and the job's skills, matched or missing."""
        return MatchResponse(
            score=round(self.matcher.score(cv_text, job_description), 4),
            skills=self.split_skills(cv_text, job_description),
            evidence=[],
            model=ModelInfo(name=self.matcher.name, version=self.matcher.version),
            warnings=["uncalibrated_score"],
        )

    def split_skills(self, cv_text: str, job_description: str) -> Skills:
        """The job's skills in the order the job names them: matched if the CV mentions them too.

        A skill counts as covered only when the CV names it (or a known spelling of it): the
        extractor doesn't guess skills a CV doesn't write, as our rating protocol doesn't.
        """
        covered = {skill.name for skill in self.skills.extract(cv_text)}
        wanted = [
            Skill(name=s.name, esco_uri=s.esco_uri) for s in self.skills.extract(job_description)
        ]
        return Skills(
            matched=[s for s in wanted if s.name in covered],
            missing=[s for s in wanted if s.name not in covered],
        )


def load_match_service() -> MatchService:
    """Build the matching service; called once at startup, never per request.

    Loading the models (the TF-IDF and skills artefacts now, embedding weights maybe later) happens
    here, before the server accepts requests, not inside the first match.
    """
    return TfidfMatchService(TfidfMatcher.load(TFIDF_ARTIFACT), SkillExtractor.load())


def get_match_service(request: Request) -> MatchService:
    """Provide the service loaded at startup (FastAPI dependency; tests override it)."""
    service: MatchService = request.app.state.match_service
    return service
