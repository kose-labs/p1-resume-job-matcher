"""FastAPI entry point.

`/health` is for infrastructure (CI smoke test, hosting health checks).
Everything the frontend calls lives under `/api/v1`, which the Vite dev server
proxies to this backend during local development.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from anyio import CapacityLimiter, to_thread
from fastapi import APIRouter, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import StringConstraints

from app.extract import PdfError, extract
from app.limits import (
    MAX_REQUEST_BYTES,
    ApiError,
    BodySizeLimit,
    keep_uploads_in_memory,
    read_cv,
)
from app.matching import MatchService, get_match_service, load_match_service
from app.observability import RequestLog, configure_logging, log_event
from app.ratelimit import RateLimit, match_limiter
from app.schemas import ErrorResponse, MatchResponse

VERSION = "0.2.0"
# How many requests may extract and match at the same time (ADR-0005). Render Free has 0.1 CPU
# and 512 MB, so more parallel work only queues on the CPU and adds to peak memory.
MATCH_CONCURRENCY = int(os.getenv("MATCH_CONCURRENCY", "2"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the model once before serving, and cap how much CPU work runs at once."""
    configure_logging()
    app.state.match_service = load_match_service()
    app.state.cpu_limiter = CapacityLimiter(MATCH_CONCURRENCY)
    yield


app = FastAPI(title="KoSe Labs service", version=VERSION, lifespan=lifespan)

keep_uploads_in_memory()
app.add_middleware(BodySizeLimit, max_bytes=MAX_REQUEST_BYTES)
# Added last, so it runs first: over-limit clients are turned away before their upload is read.
app.add_middleware(
    RateLimit,
    limiter=match_limiter,
    method="POST",
    path="/api/v1/match",
    # How many proxies in front of the app append to X-Forwarded-For (0 locally). Too low makes
    # the limit stricter; too high lets clients forge their address. See docs/deployment.md.
    trusted_hops=int(os.getenv("TRUSTED_PROXY_HOPS", "0")),
)

# One JSON log line per request (ID, method, path, status, duration), including the 413 and 429
# answers from the limits above. Never the CV or job description (see app/observability.py).
app.add_middleware(RequestLog)

# The production frontend (GitHub Pages) runs on another origin, so it needs CORS. Locally the
# Vite proxy makes requests same-origin, so CORS_ORIGINS can stay empty.
origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    # Keep this the last middleware added (the outermost), so the 413 and 429 responses from the
    # limits above also carry CORS headers; otherwise the browser hides them from the frontend.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        # Browsers only let cross-origin JavaScript read a few standard headers unless listed here.
        expose_headers=["Retry-After", "X-Request-ID"],
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Send anyone who opens the API's address to its interactive docs instead of a 404."""
    return RedirectResponse("/docs")


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


def _extract_and_match(
    service: MatchService, cv_pdf: bytes, job_description: str
) -> tuple[MatchResponse, int]:
    """The CPU-bound part of a match: read the PDF's text, then score it. Returns the page count."""
    cv = extract(cv_pdf)
    return service.match(cv.text, job_description), cv.pages


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
    request: Request,
    cv: Annotated[UploadFile, File(description="The CV as a PDF, at most 5 MB")],
    job_description: JobDescription,
    service: Annotated[MatchService, Depends(get_match_service)],
) -> MatchResponse:
    """Score how well a CV matches a job description.

    The CV is checked and kept in memory only; it is never stored or logged.
    """
    cv_pdf = await read_cv(cv)
    try:
        # CPU-bound work runs in a worker thread, at most MATCH_CONCURRENCY at once, so the event
        # loop stays free for other requests and /health (ADR-0005).
        result, pages = await to_thread.run_sync(
            _extract_and_match,
            service,
            cv_pdf,
            job_description,
            limiter=request.app.state.cpu_limiter,
        )
    except PdfError as error:
        log_event("match", outcome=error.code, cv_bytes=len(cv_pdf))
        raise ApiError(422, error.code, error.message) from error
    log_event("match", outcome="ok", cv_bytes=len(cv_pdf), pages=pages, model=result.model.name)
    return result


app.include_router(api)
