import { afterEach, expect, it, vi } from 'vitest'
import { loadSampleCv } from './sample'

afterEach(() => vi.unstubAllGlobals())

it('returns null when the sample CV cannot be fetched at all', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new TypeError('Failed to fetch'))),
  )
  expect(await loadSampleCv()).toBeNull()
})
