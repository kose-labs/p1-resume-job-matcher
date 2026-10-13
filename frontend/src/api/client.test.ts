import { afterEach, describe, expect, it, vi } from 'vitest'
import { matchCv, wakeServer } from './client'

const PDF = new File(['%PDF-1.7\n'], 'cv.pdf', { type: 'application/pdf' })
const JD = 'x'.repeat(120)

afterEach(() => vi.unstubAllGlobals())

describe('wakeServer', () => {
  it("returns the backend's version", async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(Response.json({ version: '0.1.0' }))),
    )
    expect(await wakeServer()).toBe('0.1.0')
  })

  it('says "unknown" when the server answers without a version', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('ok'))),
    )
    expect(await wakeServer()).toBe('unknown')
  })

  it('returns null when the server answers with an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('', { status: 503 }))),
    )
    expect(await wakeServer()).toBeNull()
  })
})

describe('matchCv', () => {
  it('reports the round-trip time of a successful match', async () => {
    const body = { score: 0.04, skills: { matched: [], missing: [] }, evidence: [], warnings: [] }
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(Response.json(body))),
    )
    const outcome = await matchCv(PDF, JD)
    expect(outcome.ok && outcome.elapsedMs).toBeGreaterThanOrEqual(0)
  })

  it('gives up with a timeout when the server does not answer in time', async () => {
    // A server that never answers: the request only ends when it's aborted.
    const hang = (_url: string, init: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => reject(new DOMException('', 'AbortError')))
      })
    vi.stubGlobal('fetch', vi.fn(hang))
    const outcome = await matchCv(PDF, JD, 10)
    expect(outcome).toEqual({
      ok: false,
      error: { status: 0, code: 'timeout', message: 'The server took too long to answer.' },
    })
  })

  it('explains a validation error without our error body in plain words', async () => {
    const detail = [{ loc: ['body', 'job_description'], msg: 'too short' }]
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(Response.json({ detail }, { status: 422 }))),
    )
    const outcome = await matchCv(PDF, JD)
    expect(!outcome.ok && outcome.error.code).toBe('invalid_input')
  })

  it('falls back to a generic failure for an unexpected error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve(new Response('oops', { status: 500 }))),
    )
    const outcome = await matchCv(PDF, JD)
    expect(!outcome.ok && outcome.error).toMatchObject({ status: 500, code: 'unknown_error' })
  })
})
