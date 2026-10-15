import type { Theme } from '../lib/theme'
import controls from '../styles/controls.module.css'
import { ThemeToggle } from './ThemeToggle'
import styles from './TopBar.module.css'

export type Server = 'waking' | 'ready' | 'down'

export const REPO_URL = 'https://github.com/kose-labs/p1-resume-job-matcher'

type Props = {
  apiVersion: string | null
  server: Server
  onRetry: () => void
  theme: Theme
  onThemeChange: (theme: Theme) => void
}

/** Wordmark, product name and API version on the left; server status, theme and source link on the right. */
export function TopBar({ apiVersion, server, onRetry, theme, onThemeChange }: Props) {
  return (
    <header className={styles.bar}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <span className={styles.wordmark}>KoSe Labs</span>
          <span className={styles.separator} aria-hidden="true">
            /
          </span>
          <h1 className={styles.product}>Resume–Job Matcher</h1>
          {apiVersion && (
            <span className={styles.badge} title="Backend API version">
              api {apiVersion}
            </span>
          )}
        </div>
        <div className={styles.actions}>
          <p role="status" className={styles.status} data-server={server}>
            <span className={styles.dot} aria-hidden="true" />
            {server === 'waking' && 'Waking up the server…'}
            {server === 'ready' && 'Server ready'}
            {server === 'down' && (
              <>
                Server not answering
                <button type="button" className={controls.textButton} onClick={onRetry}>
                  Retry
                </button>
              </>
            )}
          </p>
          <ThemeToggle theme={theme} onChange={onThemeChange} />
          <a className={styles.link} href={REPO_URL}>
            GitHub
          </a>
        </div>
      </div>
    </header>
  )
}
