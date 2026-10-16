import { SCORE_BANDS } from '../lib/scoreBands'
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
            The score is the cosine similarity between TF-IDF vectors of the CV and the job
            description: how much the two share the terms that are distinctive across 3,000 public
            job posts. It is not a probability of being hired. On 40 CV–job pairs we rated by hand,
            its ranking agreed moderately with ours (Spearman ρ 0.66), but the raw number has no
            meaning on its own.
          </p>
          <p>
            The bands are fitted to our ratings of those pairs: low below {SCORE_BANDS.moderate},
            moderate up to {SCORE_BANDS.strong}, strong from {SCORE_BANDS.strong}. Compare several
            jobs against the same CV rather than reading one number on its own.
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
