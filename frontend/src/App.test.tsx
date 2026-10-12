import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { MatchResponse } from './api/client'
import { SAMPLE_JD } from './sample'

const JD =
  'We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. '.repeat(2)

const RESULT: MatchResponse = {
  score: 0.72,
  skills: { matched: [{ name: 'Python', esco_uri: null }], missing: [{ name: 'Kubernetes' }] },
  evidence: [
    { requirement: 'REST APIs in Python', cv_excerpt: 'Built FastAPI services', similarity: 0.81 },
  ],
  model: { name: 'tfidf-baseline', version: '0.1.0' },
  warnings: [],
}

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

/** Stub fetch: the version check answers, and /match answers with `match()`. */
function fakeApi(match: () => Promise<Response>, versionOk = true, sampleOk = true) {
  const fetchMock = vi.fn((input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input)
    if (url.endsWith('/api/v1/version')) {
      return versionOk ? Promise.resolve(json({ version: '0.1.0' })) : Promise.reject(new Error())
    }
    if (url.endsWith('/api/v1/match')) return match()
    if (url.endsWith('/sample-cv.pdf')) {
      const body = sampleOk ? '%PDF-1.3' : 'missing'
      return Promise.resolve(new Response(body, { status: sampleOk ? 200 : 404 }))
    }
    return Promise.reject(new Error(`unexpected request to ${url}`))
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function pdf(name = 'cv.pdf', type = 'application/pdf'): File {
  return new File(['%PDF-1.7\n'], name, { type })
}

function fillForm(file: File = pdf(), jobDescription = JD) {
  fireEvent.change(screen.getByLabelText('Job description'), { target: { value: jobDescription } })
  fireEvent.change(screen.getByLabelText(/^CV/), { target: { files: [file] } })
}

afterEach(() => vi.unstubAllGlobals())

describe('server wake-up', () => {
  it('says it is waking the server, then that it is ready', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Waking up the server')
    expect(await screen.findByText('Server ready.')).toBeInTheDocument()
  })

  it('offers a retry when the server does not answer', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)), false)
    render(<App />)
    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }))
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('form validation', () => {
  it('keeps Match disabled until there is a long enough job description and a PDF', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const button = screen.getByRole('button', { name: 'Match' })
    expect(button).toBeDisabled()
    fillForm(pdf(), 'too short')
    expect(button).toBeDisabled()
    expect(screen.getByText(/at least 100/)).toBeInTheDocument()
    fillForm()
    expect(button).toBeEnabled()
  })

  it('rejects a file that is not a PDF without sending it', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm(new File(['hello'], 'cv.docx', { type: 'application/msword' }))
    expect(screen.getByRole('alert')).toHaveTextContent('The CV must be a PDF file.')
    expect(screen.getByRole('button', { name: 'Match' })).toBeDisabled()
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/match'), expect.anything())
  })

  it('clears the chosen CV when the file picker is cancelled', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm()
    fireEvent.change(screen.getByLabelText(/^CV/), { target: { files: [] } })
    expect(screen.getByRole('button', { name: 'Match' })).toBeDisabled()
  })

  it('does not send anything if the form is submitted without a CV', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    const { container } = render(<App />)
    fireEvent.change(screen.getByLabelText('Job description'), { target: { value: JD } })
    fireEvent.submit(container.querySelector('form')!)
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/match'), expect.anything())
  })

  it('rejects a CV over 5 MB without sending it', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const big = pdf()
    Object.defineProperty(big, 'size', { value: 5 * 1024 * 1024 + 1 })
    fillForm(big)
    expect(screen.getByRole('alert')).toHaveTextContent('5 MB or smaller')
  })
})

describe('matching', () => {
  it('sends the CV and job description, then shows the result', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))

    expect(await screen.findByText('Match score: 72%')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText(/Built FastAPI services/)).toBeInTheDocument()
    expect(screen.getByText('Model: tfidf-baseline v0.1.0')).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Match result' })).toHaveFocus()

    const [, init] = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/match'))!
    const body = (init as RequestInit).body as FormData
    expect(body.get('job_description')).toBe(JD)
    expect((body.get('cv') as File).name).toBe('cv.pdf')
  })

  it('shows a loading state while matching', async () => {
    let answer: (response: Response) => void = () => {}
    fakeApi(() => new Promise((resolve) => (answer = resolve)))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByRole('button', { name: 'Matching…' })).toBeDisabled()
    answer(json(RESULT))
    expect(await screen.findByText('Match score: 72%')).toBeInTheDocument()
  })

  it('explains an uncalibrated score and copes with no skills or evidence', async () => {
    const bare = { ...RESULT, score: 0.04, skills: { matched: [], missing: [] }, evidence: [] }
    fakeApi(() => Promise.resolve(json({ ...bare, warnings: ['uncalibrated_score'] })))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByText(/not yet calibrated/)).toBeInTheDocument()
    expect(screen.getByText('Text similarity: 0.04')).toBeInTheDocument()
    expect(screen.queryByText(/Match score/)).not.toBeInTheDocument()
    expect(screen.getByText(/No specific skills were recognised/)).toBeInTheDocument()
    expect(screen.queryByText('None found.')).not.toBeInTheDocument()
    expect(screen.queryByText('Why this score')).not.toBeInTheDocument()
  })

  it('says which side is empty when only one skill list has entries', async () => {
    const skills = { matched: [], missing: [{ name: 'Kubernetes' }] }
    fakeApi(() => Promise.resolve(json({ ...RESULT, skills })))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText('None found.')).toBeInTheDocument()
    expect(screen.queryByText(/No specific skills were recognised/)).not.toBeInTheDocument()
  })

  it('says nothing is missing when the CV covers every recognised skill', async () => {
    const skills = { matched: [{ name: 'Python', esco_uri: null }], missing: [] }
    fakeApi(() => Promise.resolve(json({ ...RESULT, skills })))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByText('Python')).toBeInTheDocument()
    expect(screen.getByText('None.')).toBeInTheDocument()
  })

  it('shows no calibration note without the warning', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByText('Match score: 72%')).toBeInTheDocument()
    expect(screen.queryByText(/not yet calibrated/)).not.toBeInTheDocument()
  })
})

describe('errors from the API', () => {
  async function submitAndGetAlert(response: Response) {
    fakeApi(() => Promise.resolve(response))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    return screen.findByRole('alert')
  }

  it("shows the API's own message", async () => {
    const response = json(
      { detail: { code: 'unsupported_file_type', message: 'The CV must be a PDF file.' } },
      415,
    )
    expect(await submitAndGetAlert(response)).toHaveTextContent('The CV must be a PDF file.')
  })

  it('says when to retry after hitting the rate limit', async () => {
    const response = json(
      { detail: { code: 'rate_limited', message: 'Too many requests.' } },
      429,
      { 'Retry-After': '42' },
    )
    expect(await submitAndGetAlert(response)).toHaveTextContent('try again in 42 seconds')
  })

  it('explains validation errors in plain words', async () => {
    const response = json({ detail: [{ loc: ['body', 'job_description'], msg: 'too short' }] }, 422)
    expect(await submitAndGetAlert(response)).toHaveTextContent('check the job description')
  })

  it('falls back to a generic message for unexpected errors', async () => {
    expect(await submitAndGetAlert(new Response('oops', { status: 500 }))).toHaveTextContent(
      'Something went wrong',
    )
  })

  it('reports when the server cannot be reached', async () => {
    fakeApi(() => Promise.reject(new TypeError('Failed to fetch')))
    render(<App />)
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Match' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't reach the server")
  })
})

describe('sample data and the CV drop zone', () => {
  const dropZone = () => screen.getByText(/Drop your PDF here/).closest('label')!

  it('fills in the sample job description and CV', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Use sample data' }))
    expect(await screen.findByText('sample-cv.pdf')).toBeInTheDocument()
    expect(screen.getByLabelText('Job description')).toHaveValue(SAMPLE_JD)
    expect(screen.getByRole('button', { name: 'Match' })).toBeEnabled()
  })

  it('says when the sample CV cannot be loaded', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)), true, false)
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Use sample data' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load the sample CV")
  })

  it('accepts a PDF dropped onto the drop zone', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.change(screen.getByLabelText('Job description'), { target: { value: JD } })
    fireEvent.dragOver(dropZone())
    expect(dropZone()).toHaveClass('dragging')
    fireEvent.dragLeave(dropZone())
    expect(dropZone()).not.toHaveClass('dragging')
    fireEvent.drop(dropZone(), { dataTransfer: { files: [pdf()] } })
    expect(screen.getByText('cv.pdf')).toBeInTheDocument()
    expect(screen.getByText(/1 KB/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Match' })).toBeEnabled()
  })

  it('ignores a drop without a file', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.drop(dropZone(), { dataTransfer: { files: [] } })
    expect(screen.getByText(/Drop your PDF here/)).toBeInTheDocument()
  })

  it('shows the size of a larger CV in MB', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const cv = pdf()
    Object.defineProperty(cv, 'size', { value: 2 * 1024 * 1024 })
    fillForm(cv)
    expect(screen.getByText(/2\.0 MB/)).toBeInTheDocument()
  })
})
