import { useEffect, useState } from 'react'

/** "system" follows the operating system's light or dark setting. */
export type Theme = 'system' | 'light' | 'dark'

const KEY = 'theme'
export const THEME_ORDER: Theme[] = ['system', 'light', 'dark']

/** The saved choice, or "system". Storage can be blocked (private windows), so failures are ignored. */
export function readTheme(): Theme {
  try {
    const saved = localStorage.getItem(KEY)
    return saved === 'light' || saved === 'dark' ? saved : 'system'
  } catch {
    return 'system'
  }
}

/** Apply a theme to the page: tokens.css switches colours on <html data-theme>. */
export function applyTheme(theme: Theme): void {
  if (theme === 'system') delete document.documentElement.dataset.theme
  else document.documentElement.dataset.theme = theme
}

/** The current theme and a setter that applies and remembers it. */
export function useTheme(): [Theme, (theme: Theme) => void] {
  const [theme, setTheme] = useState<Theme>(readTheme)
  useEffect(() => {
    applyTheme(theme)
    try {
      if (theme === 'system') localStorage.removeItem(KEY)
      else localStorage.setItem(KEY, theme)
    } catch {
      // Not saved; the choice still applies until the page is closed.
    }
  }, [theme])
  return [theme, setTheme]
}
