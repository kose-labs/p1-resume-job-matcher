# P1: Resume–Job Matcher, Project Plan

**Size:** minor (≤10 d) · **Dates:** 2026-10-09 → 2026-10-18
**ML lead:** Kobi · **Eng lead:** Semanu · **Security:** Semanu

## Problem (2–3 sentences)
*Kobi (K1).*

## Demo (what a recruiter sees in 30 s)
Paste a job description, upload a CV as a PDF, press **Match**. Within a few seconds the page shows a
match score, the skills the CV covers and misses, and the CV sentences that back up the score.
The CV is processed in memory and never stored.

## Scope (frozen on day 1)
**In V1** (engineering side; Kobi adds the ML side):
- One page: JD text box + CV PDF upload → score, skills (matched / missing), evidence.
- `POST /api/v1/match` as specified below, with validation, size limit and rate limit.
- Text-based PDFs only (one or two columns); scanned PDFs rejected with a clear message.
- Deployed: frontend on GitHub Pages, backend on Render Free (ADR-0002).

**Out (→ V2 issues):**
- DOCX and image (OCR) CVs.
- Accounts, history or saving results.
- Matching one CV against many jobs (or the reverse).
- Languages other than English.

## Data
*Kobi (K1, K3: ADR-0001).*

## Approach
*Kobi (K1).*

## Evaluation
*Kobi (K1): Spearman ρ against our ratings, skill extraction F1, with numeric targets.*

Engineering targets:
- `/api/v1/match` answers in **under 3 s** for a 2-page CV on a warm Render Free instance.
- Peak memory of the running API stays **under 400 MB** (Render Free gives 512 MB).
- `/health` answers in under 200 ms even while `/match` requests are running.

## Architecture (sketch)

```mermaid
flowchart LR
    U[Browser] -->|loads static site| P[GitHub Pages<br/>React + Vite + TS]
    U -->|POST /api/v1/match<br/>multipart: cv.pdf + job_description| A
    subgraph A[Render Free · FastAPI container]
        V[Validate<br/>size · type · fields · rate] --> X[PDF text extraction<br/>ADR-0003]
        X --> T[Preprocessing<br/>K6]
        T --> M[Matcher<br/>TF-IDF → embeddings<br/>K7 · K8]
        T --> S[Skill extraction<br/>ESCO · K9]
        M --> R[Response:<br/>score · skills · evidence]
        S --> R
    end
```

- **Stateless:** no database and no file storage. Each request is handled entirely in memory.
- **Model loaded once** at startup through FastAPI's lifespan and injected with `Depends` (S9), so
  requests don't pay the loading cost and tests can swap in a fake model.
- **Deployment:** GitHub Actions publishes the frontend to GitHub Pages on every merge to `main`.
  Render builds `backend/Dockerfile` on every merge to `main`. The frontend reads the backend URL from
  `VITE_API_URL`; the backend only accepts the Pages origin through `CORS_ORIGINS`.
- **Cold starts:** Render Free sleeps after 15 minutes idle and takes about a minute to wake. The
  frontend calls `/health` when the page opens and shows "Waking up the server…" until it answers.

## API contract (draft v1)

Interactive docs at `/docs`; the TypeScript client is generated from `/openapi.json` (S8).

### `POST /api/v1/match`

**Request:** `multipart/form-data`
| Field | Type | Rules |
|---|---|---|
| `cv` | file | PDF only, checked by its first bytes (`%PDF-`), not by file name or browser-sent type. At most **5 MB** and **10 pages**. Must contain extractable text. |
| `job_description` | text | **100 to 20,000 characters** after trimming whitespace. |

**Response `200 OK`:** `application/json`
```json
{
  "score": 0.72,
  "skills": {
    "matched": [{ "name": "Python", "esco_uri": "http://data.europa.eu/esco/skill/…" }],
    "missing": [{ "name": "Kubernetes", "esco_uri": null }]
  },
  "evidence": [
    {
      "requirement": "3+ years building REST APIs in Python",
      "cv_excerpt": "Built and maintained FastAPI services handling 2k requests/min",
      "similarity": 0.81
    }
  ],
  "model": { "name": "tfidf-baseline", "version": "0.1.0" },
  "warnings": ["job_description_truncated"]
}
```
| Field | Meaning |
|---|---|
| `score` | Overall match, a float from 0 to 1, rounded to 2 decimals. |
| `skills.matched` / `skills.missing` | Skills from the JD found / not found in the CV. `esco_uri` is `null` when the skill comes from our own tech dictionary instead of ESCO. |
| `evidence` | Up to 5 pairs of (JD requirement, CV sentence) that contributed most to the score, best first. |
| `model` | Which matcher produced the result, so results stay explainable as the model changes. |
| `warnings` | Non-fatal notes, e.g. `job_description_truncated`, `cv_text_short`. Empty list when none. |

### Errors

Our own errors use one shape, so the frontend can show a message and branch on `code`:
```json
{ "detail": { "code": "file_too_large", "message": "The CV must be 5 MB or smaller." } }
```
Validation errors from FastAPI (422 with a list of field problems) keep FastAPI's standard shape,
which the generated client already understands.

| Status | `code` | When |
|---|---|---|
| **413** Content Too Large | `file_too_large` | `cv` is over 5 MB. Enforced while reading the upload, not only from the `Content-Length` header. |
| **415** Unsupported Media Type | `unsupported_file_type` | `cv` doesn't start with `%PDF-`. |
| **422** Unprocessable Content | *(FastAPI list)* | A field is missing, or `job_description` is too short or too long. |
| **422** | `pdf_unreadable` | Corrupted or password-protected PDF. |
| **422** | `pdf_no_text` | No extractable text (a scanned or image-only PDF). Message suggests exporting the CV as a text PDF. |
| **422** | `pdf_too_many_pages` | More than 10 pages. |
| **429** Too Many Requests | `rate_limited` | More than **10 requests per minute** from one IP. Includes a `Retry-After` header. |
| **500** | `internal_error` | Anything unexpected. The message never contains CV text. |

### `GET /health`
`200 {"status": "ok"}`. No model work, so it stays fast for health checks and the wake-up call.

## Security & privacy
- **Never store or log CVs.** CV bytes and extracted text live only in memory for the length of
  one request. They are never written to disk, a database, logs, error messages or analytics.
- Logs record only: request ID, status code, duration, file size and page count.
- Uploads are limited (5 MB, 10 pages) and rate-limited (10/min per IP) to stop abuse of a free server.
- File type is checked by content (magic bytes), never trusted from the file name.
- CORS allows only the GitHub Pages origin. No cookies or accounts, so no session data to protect.
- Secrets live in GitHub and Render settings, never in git. gitleaks runs in pre-commit and CI;
  Dependabot and GitHub secret scanning with push protection are on.
- Test fixtures are synthetic PDFs only. Real CVs used for evaluation stay in `data/` (git-ignored)
  on our own machines.

## Risks & fallbacks
| Risk | Likelihood | Fallback |
|---|---|---|
| Model doesn't fit in Render Free's 512 MB | Medium | ONNX-based embeddings (fastembed) or static embeddings (model2vec) instead of PyTorch; TF-IDF baseline always fits |
| Cold start (≈1 min) looks broken to a visitor | High | "Waking up the server…" state; wake the API when the page loads |
| Two-column CVs extracted in the wrong reading order | Medium | Parser chosen on two-column samples (ADR-0003); fall back to layout-aware extraction |
| Abuse of the public endpoint (large files, floods) | Low | Size, page and rate limits above |
| CV text leaking through logs or errors | Low | Logging policy above, plus a test that a CV's text never appears in log output |
| Render Free limits change or the service is suspended | Low | Same Dockerfile runs on another free host; frontend only needs a new `VITE_API_URL` |

## Milestones
| Day | Milestone | Owner |
|---|---|---|
| 1 (10-09) | Plan, ADR-0001/0002, repo scaffold with CI green, security baseline, kickoff posts | Both |
| 2 (10-10) | Evaluation corpus collected; PDF parser chosen (ADR-0003) | Kobi · Semanu |
| 3 (10-11) | TF-IDF baseline scores; `/api/v1/match` skeleton with validation | Kobi · Semanu |
| 4 (10-12) | Embeddings (ADR-0004); frontend upload form via generated client | Kobi · Semanu |
| 5 (10-13) | Skill extraction with F1; model lifecycle and concurrency; mid-project check | Both |
| 6–10 | *Set at the mid-project check* | Both |
| 10 (10-18) | Launch: Definition of Done met, deployed, launch posts | Both |

## Learning goals
**Semanu (engineering):** validating uploads safely (magic bytes, streaming size limits), designing
a stable API contract and generating a typed client from it, model lifecycle and `def` vs `async`
in FastAPI, rate limiting, CORS, and privacy-by-design for personal data.

**Kobi (ML):** *K1.*
