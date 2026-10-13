import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useTheme } from '../lib/theme'
import { ThemeToggle } from './ThemeToggle'

function Harness() {
  const [theme, setTheme] = useTheme()
  return <ThemeToggle theme={theme} onChange={setTheme} />
}

afterEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  delete document.documentElement.dataset.theme
})

describe('theme toggle', () => {
  it('cycles system → light → dark → system, applying and remembering each', () => {
    render(<Harness />)
    const button = () => screen.getByRole('button', { name: /^Theme:/ })
    expect(button()).toHaveAccessibleName('Theme: System')

    fireEvent.click(button())
    expect(button()).toHaveAccessibleName('Theme: Light')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('theme')).toBe('light')

    fireEvent.click(button())
    expect(document.documentElement.dataset.theme).toBe('dark')

    fireEvent.click(button())
    expect(button()).toHaveAccessibleName('Theme: System')
    expect(document.documentElement.dataset.theme).toBeUndefined()
    expect(localStorage.getItem('theme')).toBeNull()
  })

  it('still switches when the choice cannot be saved', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    render(<Harness />)
    fireEvent.click(screen.getByRole('button', { name: /^Theme:/ }))
    expect(document.documentElement.dataset.theme).toBe('light')
  })

  it('names the next theme in its tooltip', () => {
    render(<ThemeToggle theme="dark" onChange={() => {}} />)
    expect(screen.getByRole('button')).toHaveAttribute('title', 'Switch to system theme')
  })
})
