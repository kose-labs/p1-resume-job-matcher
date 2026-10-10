// Typed calls to the backend. Every type comes from schema.d.ts, which is generated from the
// backend's OpenAPI schema (npm run api:schema, then npm run api:types), so a contract change
// shows up as a compile error here instead of a runtime surprise.
import type { components, paths } from './schema'

export type MatchResponse = components['schemas']['MatchResponse']
type ErrorResponse = components['schemas']['ErrorResponse']

// Mirrors the API contract; the backend enforces the same limits.
export const MAX_CV_BYTES = 5 * 1024 * 1024
export const JD_MIN = 100
export const JD_MAX = 20_000

// In dev the Vite proxy forwards /api to the backend; in production this is the backend URL.
const API_URL = import.meta.env.VITE_API_URL ?? ''

const VERSION_PATH: keyof paths = '/api/v1/version'
const MATCH_PATH: keyof paths = '/api/v1/match'

export type ApiFailure = {
  status: number
  code: string
  message: string
  retryAfterSeconds?: number
}

export type MatchOutcome = { ok: true; data: MatchResponse } | { ok: false; error: ApiFailure }

/** Ask the backend for its version; true once it answers. Also wakes a sleeping server. */
export async function wakeServer(): Promise<boolean> {
  try {
    return (await fetch(`${API_URL}${VERSION_PATH}`)).ok
  } catch {
    return false
  }
}

/** Upload a CV with a job description and return the match, or a typed failure. */
export async function matchCv(cv: File, jobDescription: string): Promise<MatchOutcome> {
  const form = new FormData()
  form.append('cv', cv)
  form.append('job_description', jobDescription)

  let response: Response
  try {
    response = await fetch(`${API_URL}${MATCH_PATH}`, { method: 'POST', body: form })
  } catch {
    return { ok: false, error: { status: 0, code: 'network_error', message: NETWORK_ERROR } }
  }
  if (response.ok) {
    return { ok: true, data: (await response.json()) as MatchResponse }
  }
  return { ok: false, error: await readFailure(response) }
}

const NETWORK_ERROR = "Couldn't reach the server. Check your connection and try again."
const INVALID_INPUT = 'Please check the job description and the CV, then try again.'

async function readFailure(response: Response): Promise<ApiFailure> {
  const retryAfter = Number(response.headers.get('Retry-After'))
  const failure: ApiFailure = {
    status: response.status,
    code: 'unknown_error',
    message: 'Something went wrong on our side. Please try again.',
    ...(retryAfter > 0 && { retryAfterSeconds: retryAfter }),
  }
  const body: unknown = await response.json().catch(() => null)
  if (isErrorResponse(body)) {
    return { ...failure, code: body.detail.code, message: body.detail.message }
  }
  if (response.status === 422) {
    return { ...failure, code: 'invalid_input', message: INVALID_INPUT }
  }
  return failure
}

function isErrorResponse(body: unknown): body is ErrorResponse {
  const detail = (body as { detail?: { code?: unknown; message?: unknown } } | null)?.detail
  return typeof detail?.code === 'string' && typeof detail.message === 'string'
}
