import { afterEach, describe, expect, it, vi } from 'vitest'
import { describeFailure } from './errors'
import { FIT_BANDS, fitPercent, scoreBand, shownFit } from './scoreBands'
import { resultSummary } from './summary'
import { applyTheme, readTheme } from './theme'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('scoreBand', () => {
  it.each([
    [0, 'Low'],
    [0.037, 'Low'],
    [0.0372, 'Moderate'],
    [0.0412, 'Moderate'],
    [0.0529, 'Moderate'],
    [0.0531, 'Strong'],
    [0.5, 'Strong'],
  ])('reads %s as %s', (score, band) => {
    expect(scoreBand(score)).toBe(band)
  })

  it('never contradicts the shown fit', () => {
    for (let score = 0; score <= 0.2; score += 0.0001) {
      const fit = shownFit(score)
      const band = fit >= 60 ? 'Strong' : fit >= 45 ? 'Moderate' : 'Low'
      expect(scoreBand(score)).toBe(band)
    }
  })
})

describe('fitPercent', () => {
  it.each([
    [0.04, 46],
    [0.055, 59],
    [0.11, 82],
  ])('reads %s as %s%%, as evaluate.py calibrate reports', (score, percent) => {
    expect(Math.round(fitPercent(score) * 100)).toBe(percent)
  })

  it('only rises, so the ranking of pairs never changes', () => {
    const scores = [0, 0.001, 0.01, 0.03, 0.05, 0.08, 0.13, 0.5, 1]
    const fits = scores.map(fitPercent)
    fits.slice(1).forEach((fit, i) => expect(fit).toBeGreaterThan(fits[i]))
    expect(fits[0]).toBeGreaterThanOrEqual(0)
    expect(fits.at(-1)).toBeLessThan(1)
  })

  it('is shown rounded to the nearest 5%', () => {
    expect(shownFit(0.11)).toBe(80)
    expect(shownFit(0.0412)).toBe(45)
    expect(shownFit(0)).toBe(0)
  })

  it('puts the band thresholds on the 5% grid', () => {
    expect(FIT_BANDS.moderate % 5).toBe(0)
    expect(FIT_BANDS.strong % 5).toBe(0)
  })
})

describe('resultSummary', () => {
  const result = {
    score: 0.11,
    skills: { matched: [{ name: 'Python' }, { name: 'Docker' }], missing: [{ name: 'Go' }] },
    evidence: [],
    model: { name: 'tfidf-baseline', version: '0.1.0' },
    warnings: ['uncalibrated_score'],
  }

  it('sums up an estimated fit and the skills in plain text', () => {
    expect(resultSummary(result)).toBe(
      [
        'Resume–Job Matcher (KoSe Labs)',
        'Strong fit (estimated fit ≈ 80%, raw similarity 0.110)',
        'Skills the CV names (2 of 3): Python, Docker',
        'Missing from the CV: Go',
        'Model: tfidf-baseline 0.1.0',
      ].join('\n'),
    )
  })

  it('uses a calibrated score as it is, and says none for an empty list', () => {
    const calibrated = {
      ...result,
      score: 0.72,
      warnings: [],
      skills: { matched: [], missing: [] },
    }
    const text = resultSummary(calibrated)
    expect(text).toContain('Match score 72%')
    expect(text).toContain('Skills the CV names (0 of 0): none')
  })
})

describe('describeFailure', () => {
  const failure = (code: string, extra = {}) => ({
    status: 400,
    code,
    message: 'API says',
    ...extra,
  })

  it('says how long to wait after the rate limit', () => {
    expect(describeFailure(failure('rate_limited', { retryAfterSeconds: 42 })).detail).toBe(
      'Wait 42 seconds, then run the match again.',
    )
    expect(describeFailure(failure('rate_limited')).detail).toBe(
      'Wait a minute, then run the match again.',
    )
  })

  it('explains a timeout as a server that may have been starting', () => {
    expect(describeFailure(failure('timeout')).title).toBe('The server took too long to answer')
  })

  it("puts a short title over the API's own message for known codes", () => {
    expect(describeFailure(failure('pdf_no_text'))).toEqual({
      title: 'This PDF looks scanned',
      detail: 'API says',
    })
  })

  it('falls back to a generic title for unknown codes', () => {
    expect(describeFailure(failure('teapot')).title).toBe('Something went wrong')
  })
})

describe('theme storage', () => {
  it('reads a saved theme and ignores anything else', () => {
    localStorage.setItem('theme', 'dark')
    expect(readTheme()).toBe('dark')
    localStorage.setItem('theme', 'neon')
    expect(readTheme()).toBe('system')
  })

  it('falls back to the system theme when storage is blocked', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(readTheme()).toBe('system')
  })

  it('sets or clears data-theme on the page', () => {
    applyTheme('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    applyTheme('system')
    expect(document.documentElement.dataset.theme).toBeUndefined()
  })
})
