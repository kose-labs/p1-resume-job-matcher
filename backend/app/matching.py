"""The matching service the API calls: built once at startup, injected into each request."""

from pathlib import Path
from typing import Protocol

import numpy as np
from fastapi import Request

from app.ml import embeddings
from app.ml.skills import SkillExtractor
from app.ml.tfidf import TfidfMatcher
from app.schemas import Evidence, MatchResponse, ModelInfo, Skill, Skills

# Fitted on public job descriptions only, rebuilt by scripts/build_tfidf_artifact.py (ADR-0006).
TFIDF_ARTIFACT = Path(__file__).parent / "ml" / "artifacts" / "tfidf-jds.json.gz"
EVIDENCE_SIZE = 5  # requirement-sentence pairs shown at most


class MatchService(Protocol):
    """Anything that can score a CV's text against a job description."""

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the match result for one CV and one job description."""
        ...


class TfidfMatchService:
    """Scores with the TF-IDF baseline (K7), fitted on public job descriptions only, and splits the
    job's skills (K9) into those the CV mentions and those it doesn't.

    Raw cosine scores are small until they're calibrated against our ratings (J2), so every result
    carries the `uncalibrated_score` warning. Evidence pairs requirements with CV sentences by
    TF-IDF, since no embedding model ships in V1 (ADR-0004).
    """

    def __init__(self, matcher: TfidfMatcher, skills: SkillExtractor) -> None:
        """Wrap a fitted matcher and a loaded skill extractor."""
        self.matcher = matcher
        self.skills = skills

    def match(self, cv_text: str, job_description: str) -> MatchResponse:
        """Return the TF-IDF cosine similarity, the job's skills and the evidence behind them."""
        evidence, truncated = self.evidence(cv_text, job_description)
        return MatchResponse(
            score=round(self.matcher.score(cv_text, job_description), 4),
            skills=self.split_skills(cv_text, job_description),
            evidence=evidence,
            model=ModelInfo(name=self.matcher.name, version=self.matcher.version),
            warnings=["uncalibrated_score", *(["cv_truncated"] if truncated else [])],
        )

    def evidence(self, cv_text: str, job_description: str) -> tuple[list[Evidence], bool]:
        """The job's requirements paired with the CV sentences that back them up, best first.

        Uses K8's chunking (requirement sentences x CV sentences, the CV capped at its first
        chunks) with TF-IDF cosine for similarity. TF-IDF also rates sentences that only share
        generic words ("practical experience"), so a sentence counts as evidence for a
        requirement only if the two name at least one skill in common. Returns the pairs, and
        whether the CV was longer than the part searched.
        """
        requirements = embeddings.jd_requirements(job_description)
        chunks = embeddings.cv_sentences(cv_text, limit=None)
        sentences = chunks[: embeddings.CV_CHUNK_LIMIT]
        truncated = len(chunks) > embeddings.CV_CHUNK_LIMIT
        if not requirements or not sentences:
            return [], truncated
        # score_matrix compares every text of the first list with every text of the second.
        similarity = self.matcher.score_matrix([r.text for r in requirements], sentences)
        wanted = [{s.name for s in self.skills.extract(r.text)} for r in requirements]
        offered = [{s.name for s in self.skills.extract(text)} for text in sentences]
        shares = np.array([[bool(w & o) for o in offered] for w in wanted], dtype=bool)
        picked = embeddings.pick_evidence(
            requirements,
            sentences,
            np.where(shares, similarity, 0.0),
            EVIDENCE_SIZE,
            min_similarity=1e-9,  # only pairs that share a skill and some terms
        )
        pairs = [
            Evidence(requirement=e.requirement, cv_excerpt=e.cv_excerpt, similarity=e.similarity)
            for e in picked
        ]
        return pairs, truncated

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
