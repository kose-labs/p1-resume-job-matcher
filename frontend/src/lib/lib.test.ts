import { afterEach, describe, expect, it, vi } from 'vitest'
import { describeFailure } from './errors'
import { scoreBand } from './scoreBands'
import { applyTheme, readTheme } from './theme'

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
})

describe('scoreBand', () => {
  it.each([
    [0, 'Low'],
    [0.0399, 'Low'],
    [0.04, 'Moderate'],
    [0.0549, 'Moderate'],
    [0.055, 'Strong'],
    [0.5, 'Strong'],
  ])('reads %s as %s', (score, band) => {
    expect(scoreBand(score)).toBe(band)
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
