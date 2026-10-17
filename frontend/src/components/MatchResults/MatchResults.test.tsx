import { render, screen } from '@testing-library/react'
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
    expect(screen.getByText(/Run a match to see the similarity score/)).toBeInTheDocument()
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
