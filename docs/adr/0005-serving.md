# ADR-0005: Serving the model: async endpoint, CPU work in limited worker threads

**Status:** accepted by both deciders on 2026-10-18 · **Date:** 2026-10-11 · **Deciders:** Semanu
(eng lead), Kobi (review)

## Context
A match is CPU-bound: reading the PDF (pdfplumber, ADR-0003) and scoring it (TF-IDF now,
embeddings maybe later, ADR-0004). The API runs as **one process on Render Free: 0.1 CPU and
512 MB** (ADR-0002). Three things must hold under load:
- `/health` and quick requests stay fast while matches run (Render's health check, the frontend's
  "waking up" call);
- memory stays under budget even when several people upload 5 MB CVs at once;
- the model loads once, not on every request.

FastAPI offers two kinds of endpoint, and both defaults are wrong here:
- An **`async def`** endpoint runs on the event loop. Calling the model directly blocks the loop,
  so every other request, `/health` included, waits for the match to finish.
- A plain **`def`** endpoint runs in a thread pool of up to **40** threads. That keeps the loop free,
  but allows 40 matches at once: on 0.1 CPU they only queue for the processor, while each one holds
  its PDF, text and model work in memory at the same time.

## Options considered
1. **`async def`, model called directly.** Simplest. Rejected: measured with a slow fake model,
   `/health` took 1.5 s instead of milliseconds (`tests/test_serving.py`, which fails if this is
   reintroduced).
2. **Plain `def` endpoint.** Loop stays free. Rejected: no bound on parallel CPU work or memory.
3. **`async def` endpoint, CPU work in worker threads behind a limit of 2** (chosen). The endpoint
   reads the upload asynchronously, then runs extraction and matching with
   `anyio.to_thread.run_sync(..., limiter=CapacityLimiter(MATCH_CONCURRENCY))`. Extra requests
   wait their turn without blocking the loop.
4. **Process pool or several Uvicorn workers.** True parallelism, but each process loads its own
   copy of the model, multiplying memory, and 0.1 CPU gains nothing from parallel processes.
   Rejected for Render Free.

## Decision
- **Load once at startup:** FastAPI's lifespan builds the match service (`load_match_service()`)
  before the server accepts requests and stores it on `app.state`; the endpoint gets it through
  `Depends(get_match_service)`, which tests replace with fakes via `dependency_overrides`.
- **One process, one Uvicorn worker** (the Dockerfile's default).
- **CPU work in worker threads, at most `MATCH_CONCURRENCY` (default 2) at once.**

## Consequences
- Under a burst, requests queue for a free slot, so latency rises instead of memory. The rate
  limit (10 matches a minute per client) bounds how long the queue can get.
- CI checks it on every pull request: `tests/test_serving.py` (the model loads once; `/health` stays
  under 250 ms while four slow matches run; never more than two run at once) and a memory check
  that sends four near-5 MB CVs at once to the real image capped at 512 MB and fails if peak memory
  passes 400 MB (`backend/scripts/memory_check.py`).
- If the embedding model (ADR-0004) is adopted, it loads in `load_match_service()`, and the memory
  check decides whether two concurrent matches still fit or `MATCH_CONCURRENCY` drops to 1.
  (ADR-0004 kept TF-IDF, so V1 didn't need this.)
