"""FastAPI entry point.

`/health` is for infrastructure (CI smoke test, hosting health checks).
Everything the frontend calls lives under `/api/v1`, which the Vite dev server
proxies to this backend during local development.
"""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import StringConstraints

from app.limits import MAX_REQUEST_BYTES, BodySizeLimit, keep_uploads_in_memory, read_cv
from app.matching import MatchService, get_match_service
from app.ratelimit import RateLimit, match_limiter
from app.schemas import ErrorResponse, MatchResponse

VERSION = "0.1.0"

app = FastAPI(title="KoSe Labs service", version=VERSION)

keep_uploads_in_memory()
app.add_middleware(BodySizeLimit, max_bytes=MAX_REQUEST_BYTES)
# Added last, so it runs first: over-limit clients are turned away before their upload is read.
app.add_middleware(RateLimit, limiter=match_limiter, method="POST", path="/api/v1/match")

# Production frontend (e.g. on Vercel) runs on another origin, so it needs CORS.
# Locally the Vite proxy makes requests same-origin, so this list can stay empty.
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up, for CI smoke tests and hosting health checks."""
    return {"status": "ok"}


api = APIRouter(prefix="/api/v1")


@api.get("/version")
def version() -> dict[str, str]:
    """Return the running backend version, so the frontend can show what it's connected to."""
    return {"version": VERSION}


JobDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=100, max_length=20_000),
    Form(description="Job description text, 100 to 20,000 characters"),
]


@api.post(
    "/match",
    responses={
        413: {"model": ErrorResponse, "description": "CV over 5 MB (`file_too_large`)"},
        415: {"model": ErrorResponse, "description": "CV is not a PDF (`unsupported_file_type`)"},
        429: {
            "model": ErrorResponse,
            "description": "Over 10 requests a minute from one client (`rate_limited`)",
        },
    },
)
async def match(
    cv: Annotated[UploadFile, File(description="The CV as a PDF, at most 5 MB")],
    job_description: JobDescription,
    service: Annotated[MatchService, Depends(get_match_service)],
) -> MatchResponse:
    """Score how well a CV matches a job description.

    The CV is checked and kept in memory only; it is never stored or logged.
    """
    cv_pdf = await read_cv(cv)
    return service.match(cv_pdf, job_description)


app.include_router(api)
