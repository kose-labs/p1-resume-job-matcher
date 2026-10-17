import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { MatchResponse } from './api/client'
import { SAMPLE_JD } from './sample'

const JD =
  'We are hiring a backend engineer to build and run REST APIs in Python with FastAPI. '.repeat(2)

const RESULT: MatchResponse = {
  score: 0.0412,
  skills: { matched: [{ name: 'Python', esco_uri: null }], missing: [{ name: 'Kubernetes' }] },
  evidence: [],
  model: { name: 'tfidf-baseline', version: '0.1.0' },
  warnings: ['uncalibrated_score'],
}

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

/** Stub fetch: the version check, /match answered by `match()`, and the sample CV. */
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

const runButton = () => screen.getByRole('button', { name: 'Run match' })
const matchCalls = (fetchMock: ReturnType<typeof fakeApi>) =>
  fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/match'))

afterEach(() => vi.unstubAllGlobals())

describe('top bar', () => {
  it('says it is waking the server, then shows it is ready with the API version', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    expect(screen.getByRole('status')).toHaveTextContent('Waking up the server')
    expect(await screen.findByText('Server ready')).toBeInTheDocument()
    expect(screen.getByText('api 0.1.0')).toBeInTheDocument()
  })

  it('offers a retry when the server does not answer', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)), false)
    render(<App />)
    expect(await screen.findByText('Server not answering')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('inputs', () => {
  it('keeps Run match disabled until there is a long enough job description and a PDF', () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    expect(runButton()).toBeDisabled()
    fillForm(pdf(), 'too short')
    expect(runButton()).toBeDisabled()
    expect(screen.getByText('At least 100 characters')).toBeInTheDocument()
    expect(screen.getByText('9 / 20,000')).toBeInTheDocument()
    fillForm()
    expect(runButton()).toBeEnabled()
  })

  it('explains each missing input when someone tries to run an incomplete form', () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.keyDown(screen.getByLabelText('Job description'), { key: 'Enter', ctrlKey: true })
    expect(screen.getByText('Add a job description of at least 100 characters.')).toBeVisible()
    expect(screen.getByText('Choose the CV as a PDF.')).toBeVisible()

    fireEvent.change(screen.getByLabelText('Job description'), {
      target: { value: 'x'.repeat(40) },
    })
    expect(screen.getByText('Add at least 60 more characters.')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Job description'), {
      target: { value: 'x'.repeat(20_001) },
    })
    expect(screen.getByText('Shorten the job description to 20,000 characters.')).toBeVisible()
    expect(matchCalls(fetchMock)).toHaveLength(0)
  })

  it('ignores other keys pressed in the form', () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.keyDown(screen.getByLabelText('Job description'), { key: 'Enter' })
    expect(screen.queryByText('Choose the CV as a PDF.')).not.toBeInTheDocument()
    expect(matchCalls(fetchMock)).toHaveLength(0)
  })

  it('rejects a file that is not a PDF, or one over 5 MB, without sending it', () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm(new File(['hello'], 'cv.docx', { type: 'application/msword' }))
    expect(screen.getByRole('alert')).toHaveTextContent('This file is not a PDF.')
    const big = pdf()
    Object.defineProperty(big, 'size', { value: 5 * 1024 * 1024 + 1 })
    fillForm(big)
    expect(screen.getByRole('alert')).toHaveTextContent('This file is over 5 MB.')
    expect(runButton()).toBeDisabled()
    expect(matchCalls(fetchMock)).toHaveLength(0)
  })

  it('shows the chosen file with its size, and removes it', () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const big = pdf('long-cv.pdf')
    Object.defineProperty(big, 'size', { value: 2 * 1024 * 1024 })
    fillForm(big)
    expect(screen.getByText('long-cv.pdf')).toBeInTheDocument()
    expect(screen.getByText('2.0 MB')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(screen.queryByText('long-cv.pdf')).not.toBeInTheDocument()
    expect(runButton()).toBeDisabled()
  })

  it('clears the chosen CV when the file picker is cancelled', () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm()
    fireEvent.change(screen.getByLabelText(/^CV/), { target: { files: [] } })
    expect(runButton()).toBeDisabled()
    fillForm()
    fireEvent.change(screen.getByLabelText(/^CV/), { target: { files: null } })
    expect(runButton()).toBeDisabled()
  })

  it('opens the file picker from Choose and Replace', () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const picker = screen.getByLabelText(/^CV/)
    const click = vi.spyOn(picker, 'click')
    fireEvent.click(screen.getByRole('button', { name: 'choose a file' }))
    fillForm()
    fireEvent.click(screen.getByRole('button', { name: 'Replace' }))
    expect(click).toHaveBeenCalledTimes(2)
  })

  it('accepts a PDF dropped onto the CV row, and ignores a drop without a file', () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    const zone = screen.getByText(/Drop a PDF here/).parentElement!
    fireEvent.dragOver(zone)
    expect(zone).toHaveAttribute('data-dragging', 'true')
    fireEvent.dragLeave(zone)
    expect(zone).toHaveAttribute('data-dragging', 'false')
    fireEvent.drop(zone, { dataTransfer: { files: [] } })
    expect(screen.getByText(/Drop a PDF here/)).toBeInTheDocument()
    fireEvent.drop(zone, { dataTransfer: { files: [pdf()] } })
    expect(screen.getByText('cv.pdf')).toBeInTheDocument()
    expect(screen.getByText('1 KB')).toBeInTheDocument()
  })

  it('fills in the sample job description and CV', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Use sample data' }))
    expect(await screen.findByText('sample-cv.pdf')).toBeInTheDocument()
    expect(screen.getByLabelText('Job description')).toHaveValue(SAMPLE_JD)
    expect(runButton()).toBeEnabled()
  })

  it('says when the sample CV cannot be loaded', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)), true, false)
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Use sample data' }))
    expect(await screen.findByRole('alert')).toHaveTextContent("Couldn't load the sample CV")
  })
})

describe('running a match', () => {
  it('sends the CV and job description, then shows the report', async () => {
    const fetchMock = fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    expect(screen.getByText(/Run a match to see the similarity score/)).toBeInTheDocument()
    fillForm()
    fireEvent.click(runButton())

    expect(await screen.findByText('≈ 45%')).toBeInTheDocument()
    expect(screen.getByText('Moderate fit')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText(/^tfidf-baseline 0\.1\.0 · \d+ ms round trip$/)).toBeInTheDocument()

    const [[, init]] = matchCalls(fetchMock)
    const body = (init as RequestInit).body as FormData
    expect(body.get('job_description')).toBe(JD)
    expect((body.get('cv') as File).name).toBe('cv.pdf')
  })

  it('runs with Ctrl or Cmd + Enter', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    render(<App />)
    fillForm()
    fireEvent.keyDown(screen.getByLabelText('Job description'), { key: 'Enter', metaKey: true })
    expect(await screen.findByText('≈ 45%')).toBeInTheDocument()
  })

  it('shows a spinner and a skeleton while matching, and ignores repeat requests', async () => {
    let answer: (response: Response) => void = () => {}
    const fetchMock = fakeApi(() => new Promise((resolve) => (answer = resolve)))
    render(<App />)
    fillForm()
    fireEvent.click(runButton())
    const running = await screen.findByRole('button', { name: 'Running…' })
    expect(running).toHaveAttribute('aria-disabled', 'true')
    fireEvent.click(running)
    expect(screen.getByText('Running the match…')).toBeInTheDocument()
    fireEvent.keyDown(screen.getByLabelText('Job description'), { key: 'Enter', ctrlKey: true })
    expect(matchCalls(fetchMock)).toHaveLength(1)
    answer(json(RESULT))
    expect(await screen.findByText('≈ 45%')).toBeInTheDocument()
  })

  it('shows API errors with a title and what to do next', async () => {
    const message = 'This PDF has no selectable text, so it looks scanned.'
    fakeApi(() => Promise.resolve(json({ detail: { code: 'pdf_no_text', message } }, 422)))
    render(<App />)
    fillForm()
    fireEvent.click(runButton())
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('This PDF looks scanned')
    expect(alert).toHaveTextContent(message)
  })

  it('says how long to wait after hitting the rate limit', async () => {
    const detail = { code: 'rate_limited', message: 'Too many requests.' }
    fakeApi(() => Promise.resolve(json({ detail }, 429, { 'Retry-After': '42' })))
    render(<App />)
    fillForm()
    fireEvent.click(runButton())
    expect(await screen.findByRole('alert')).toHaveTextContent('Wait 42 seconds')
  })

  it('reports when the server cannot be reached', async () => {
    fakeApi(() => Promise.reject(new TypeError('Failed to fetch')))
    render(<App />)
    fillForm()
    fireEvent.click(runButton())
    expect(await screen.findByRole('alert')).toHaveTextContent("Can't reach the server")
  })
})

describe('keyboard shortcut hint', () => {
  it('shows Ctrl Enter, or ⌘ Enter on a Mac', async () => {
    fakeApi(() => Promise.resolve(json(RESULT)))
    const { unmount } = render(<App />)
    expect(screen.getByText('Ctrl Enter')).toBeInTheDocument()
    unmount()

    vi.stubGlobal('navigator', { ...navigator, userAgent: 'Mozilla/5.0 (Macintosh)' })
    vi.resetModules()
    const { default: MacApp } = await import('./App')
    render(<MacApp />)
    expect(screen.getByText('⌘ Enter')).toBeInTheDocument()
  })
})
