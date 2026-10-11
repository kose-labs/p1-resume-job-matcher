"""Request and response models for the API, matching the contract in docs/project_plan.md."""

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """A skill named in the job description."""

    name: str
    esco_uri: str | None = Field(
        default=None, description="ESCO skill URI, or null when the skill comes from our dictionary"
    )


class Skills(BaseModel):
    """Skills from the job description, split by whether the CV covers them."""

    matched: list[Skill]
    missing: list[Skill]


class Evidence(BaseModel):
    """A job requirement and the CV sentence that best supports it."""

    requirement: str
    cv_excerpt: str
    similarity: float = Field(ge=0, le=1)


class ModelInfo(BaseModel):
    """Which matcher produced a result, so results stay explainable as the model changes."""

    name: str
    version: str


class MatchResponse(BaseModel):
    """Result of matching one CV against one job description."""

    score: float = Field(ge=0, le=1, description="Overall match from 0 to 1")
    skills: Skills
    evidence: list[Evidence] = Field(max_length=5, description="Strongest supporting pairs first")
    model: ModelInfo
    warnings: list[str] = Field(description="Non-fatal notes, e.g. job_description_truncated")


class ErrorDetail(BaseModel):
    """Machine-readable code plus a message the frontend can show as is."""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Body of every error the API raises itself (not FastAPI's field validation errors)."""

    detail: ErrorDetail
