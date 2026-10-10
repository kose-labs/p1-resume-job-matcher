import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('shows the backend version when the API responds', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify({ version: '0.1.0' }), { status: 200 })),
    )
    render(<App />)
    expect(await screen.findByText('Backend connected (v0.1.0)')).toBeInTheDocument()
  })

  it('shows an error when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))
    render(<App />)
    expect(await screen.findByText(/Backend unreachable/)).toBeInTheDocument()
  })
})
