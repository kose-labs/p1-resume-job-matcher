import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { MatchResponse } from '../../api/client'
import { MatchResults } from './MatchResults'

const UNCALIBRATED: MatchResponse = {
  score: 0.0412,
  skills: { matched: [{ name: 'Python', esco_uri: null }], missing: [{ name: 'Kubernetes' }] },
  evidence: [
    { requirement: 'REST APIs in Python', cv_excerpt: 'Built FastAPI services', similarity: 0.81 },
  ],
  model: { name: 'tfidf-baseline', version: '0.1.0' },
  warnings: ['uncalibrated_score'],
}

afterEach(() => vi.restoreAllMocks())

describe('results pane states', () => {
  it('explains what will appear before the first match', () => {
    render(<MatchResults phase={{ kind: 'idle' }} />)
    expect(screen.getByText('Your result will appear here')).toBeInTheDocument()
    expect(screen.getByText('An estimated fit')).toBeInTheDocument()
    expect(screen.getByText(/never stored/)).toBeInTheDocument()
  })

  it('shows a busy skeleton while the match runs', () => {
    const { container } = render(<MatchResults phase={{ kind: 'loading' }} />)
    expect(container.firstChild).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Running the match…')).toBeInTheDocument()
  })

  it('shows a failure with what to do next', () => {
    const error = { status: 0, code: 'network_error', message: 'offline' }
    render(<MatchResults phase={{ kind: 'failed', error }} />)
    expect(screen.getByRole('alert')).toHaveTextContent("Can't reach the server")
    expect(screen.getByRole('alert')).toHaveTextContent('Check your internet connection')
  })

  it('shows the uncalibrated score with its band, caveat, skills, evidence and metadata', () => {
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 1412 }} />)
    expect(screen.getByText('Estimated fit · TF-IDF')).toBeInTheDocument()
    expect(screen.getByText('Moderate fit')).toBeInTheDocument()
    expect(screen.getByText('≈ 45%')).toBeInTheDocument()
    expect(screen.getByRole('meter')).toHaveAccessibleName('Moderate fit, about 45%')
    expect(screen.getByText(/raw similarity 0\.041/)).toBeInTheDocument()
    expect(screen.getByText(/Not a probability of being hired/)).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Kubernetes')).toBeInTheDocument()
    expect(screen.getByText('Built FastAPI services')).toBeInTheDocument()
    expect(screen.getByText('0.81')).toBeInTheDocument()
    expect(screen.getByText('tfidf-baseline 0.1.0 · 1,412 ms round trip')).toBeInTheDocument()
  })

  it('explains the evidence, and says when a long CV was only partly searched', () => {
    const { rerender } = render(
      <MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />,
    )
    expect(screen.getByText(/CV sentences that name a skill/)).toBeInTheDocument()
    expect(screen.queryByText(/only its first part/)).not.toBeInTheDocument()
    const long = { ...UNCALIBRATED, warnings: ['uncalibrated_score', 'cv_truncated'] }
    rerender(<MatchResults phase={{ kind: 'done', result: long, elapsedMs: 5 }} />)
    expect(screen.getByText(/only its first part \(about 4 pages\) was searched/)).toBeVisible()
  })

  it('tints the score card by band and says what the band means', () => {
    const { container } = render(
      <MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />,
    )
    expect(container.querySelector('[data-band]')).toHaveAttribute('data-band', 'moderate')
    expect(screen.getByText('The CV covers part of what this job asks for.')).toBeVisible()
  })

  it('counts how many of the job skills the CV names, with a tip for the missing ones', () => {
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    expect(screen.getByText(/The CV names/)).toHaveTextContent(
      "The CV names 1 of the job's 2 skills",
    )
    expect(screen.getByText(/Have any of the missing skills\?/)).toBeVisible()
  })

  it('says a Low fit shares few words and skills, without claiming more', () => {
    const result = { ...UNCALIBRATED, score: 0.01 }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(
      screen.getByText("The CV shares few of this job's distinctive words and skills."),
    ).toBeVisible()
  })

  it('leaves out the tip when nothing is missing', () => {
    const result = { ...UNCALIBRATED, skills: { matched: [{ name: 'Go' }], missing: [] } }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.queryByText(/Have any of the missing skills/)).not.toBeInTheDocument()
  })

  it('keeps a very high score below 100%', () => {
    const result = { ...UNCALIBRATED, score: 0.34 }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.getByText('Strong fit')).toBeInTheDocument()
    expect(screen.getByText('≈ 95%')).toBeInTheDocument()
    expect(screen.getByRole('meter')).toHaveAttribute('value', '97')
  })

  it('shows a calibrated score as a percentage, without bands or caveat', () => {
    const result = { ...UNCALIBRATED, score: 0.72, warnings: [] }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.getByText('Match score · TF-IDF')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.queryByText(/raw similarity/)).not.toBeInTheDocument()
  })

  it('names an unknown model as the API reports it', () => {
    const result = { ...UNCALIBRATED, model: { name: 'minilm-chunked', version: '0.2.0' } }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.getByText('Estimated fit · minilm-chunked')).toBeInTheDocument()
  })

  it('says so when no skills were identified, and hides empty evidence', () => {
    const result = { ...UNCALIBRATED, skills: { matched: [], missing: [] }, evidence: [] }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.getByText('No skills were identified in this job description.')).toBeVisible()
    expect(screen.queryByText('Evidence')).not.toBeInTheDocument()
  })

  it('marks an empty side of the skills breakdown', () => {
    const result = { ...UNCALIBRATED, skills: { matched: [], missing: [{ name: 'Go' }] } }
    render(<MatchResults phase={{ kind: 'done', result, elapsedMs: 5 }} />)
    expect(screen.getByText('None')).toBeInTheDocument()
    expect(screen.getByText('Go')).toBeInTheDocument()
  })
})

describe('copying a result', () => {
  afterEach(() => {
    // jsdom has no clipboard; each test adds its own.
    delete (navigator as { clipboard?: unknown }).clipboard
  })

  function withClipboard(writeText: (text: string) => Promise<void>) {
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  }

  it('copies a text summary and says so for two seconds', async () => {
    vi.useFakeTimers()
    const writeText = vi.fn((_text: string) => Promise.resolve())
    withClipboard(writeText)
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Copy results' })))
    expect(writeText.mock.calls[0][0]).toContain('Moderate fit (estimated fit ≈ 45%')
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()
    act(() => vi.advanceTimersByTime(2000))
    expect(screen.getByRole('button', { name: 'Copy results' })).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('keeps the button as it was when the browser refuses', async () => {
    withClipboard(() => Promise.reject(new Error('denied')))
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Copy results' })))
    expect(screen.getByRole('button', { name: 'Copy results' })).toBeInTheDocument()
  })

  it('hides the button where there is no clipboard', () => {
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    expect(screen.queryByRole('button', { name: 'Copy results' })).not.toBeInTheDocument()
  })
})

describe('bringing results into view', () => {
  it('scrolls to a new result that is below the screen, as on a phone', () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      top: window.innerHeight + 200,
    } as DOMRect)
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    expect(scroll).toHaveBeenCalled()
  })

  it('leaves the page alone when the result is already in view', () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    render(<MatchResults phase={{ kind: 'done', result: UNCALIBRATED, elapsedMs: 5 }} />)
    expect(scroll).not.toHaveBeenCalled()
  })
})
