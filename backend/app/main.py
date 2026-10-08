"""FastAPI entry point.

`/health` is for infrastructure (CI smoke test, hosting health checks).
Everything the frontend calls lives under `/api/v1`, which the Vite dev server
proxies to this backend during local development.
"""

import os

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

VERSION = "0.1.0"

app = FastAPI(title="KoSe Labs service", version=VERSION)

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


app.include_router(api)
