import type { ReactNode } from 'react'
import styles from './AppShell.module.css'

type Props = {
  topBar: ReactNode
  inputs: ReactNode
  results: ReactNode
  footer: ReactNode
}

/** Page frame: top bar, a two-pane workspace (inputs left, results right) and a footer. */
export function AppShell({ topBar, inputs, results, footer }: Props) {
  return (
    <div className={styles.shell}>
      {topBar}
      <main className={styles.workspace}>
        <section className={styles.pane} aria-labelledby="inputs-title">
          <h2 id="inputs-title" className={styles.paneTitle}>
            Inputs
          </h2>
          {inputs}
        </section>
        <section className={`${styles.pane} ${styles.results}`} aria-labelledby="results-title">
          <div className={styles.sticky}>
            <h2 id="results-title" className={styles.paneTitle}>
              Results
            </h2>
            {results}
          </div>
        </section>
      </main>
      {footer}
    </div>
  )
}
