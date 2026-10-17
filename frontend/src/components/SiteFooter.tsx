import { FIT_BANDS } from '../lib/scoreBands'
import { SAMPLE_CV_URL } from '../sample'
import styles from './SiteFooter.module.css'
import { REPO_URL } from './TopBar'

/** "About this score" in plain terms, the privacy statement and the source link. */
export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <details className={styles.about}>
        <summary className={styles.summary}>About this score</summary>
        <div className={styles.body}>
          <p>
            The matcher measures how much the CV and the job description share the terms that are
            distinctive across 3,000 public job posts (TF-IDF cosine similarity). That raw number is
            small and hard to read, so the page turns it into an estimated fit: how we would likely
            rate the pair from 1 (no fit, 0%) to 5 (strong fit, 100%), learned from 40 CV–job pairs
            we rated by hand. On those pairs the matcher ranked pairs much as we did (Spearman ρ
            0.66). It is not a probability of being hired.
          </p>
          <p>
            Bands, fitted to the same ratings: low below {FIT_BANDS.moderate}%, moderate up to{' '}
            {FIT_BANDS.strong}%, strong from {FIT_BANDS.strong}%. Compare several jobs against the
            same CV rather than reading one number on its own.
          </p>
          <p>
            Only text-based PDFs can be read; scanned CVs are rejected. The sample CV is fictional (
            <a href={SAMPLE_CV_URL} download>
              download it
            </a>
            ).
          </p>
        </div>
      </details>
      <p className={styles.line}>
        CVs are processed in memory and never stored. Logs record request size and timing, never CV
        or job text. <a href={REPO_URL}>Source on GitHub</a>
      </p>
    </footer>
  )
}
