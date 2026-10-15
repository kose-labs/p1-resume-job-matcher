import { THEME_ORDER, type Theme } from '../lib/theme'
import styles from './ThemeToggle.module.css'

const LABELS: Record<Theme, string> = { system: 'System', light: 'Light', dark: 'Dark' }

/** Cycles the theme: system → light → dark. The button says which theme is active. */
export function ThemeToggle({ theme, onChange }: { theme: Theme; onChange: (t: Theme) => void }) {
  const next = THEME_ORDER[(THEME_ORDER.indexOf(theme) + 1) % THEME_ORDER.length]
  return (
    <button
      type="button"
      className={styles.toggle}
      onClick={() => onChange(next)}
      aria-label={`Theme: ${LABELS[theme]}`}
      title={`Switch to ${LABELS[next].toLowerCase()} theme`}
    >
      {LABELS[theme]}
    </button>
  )
}
