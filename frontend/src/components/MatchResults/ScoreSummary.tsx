import type { MatchResponse } from '../../api/client'
import { METER_MAX, SCORE_BANDS, scoreBand } from '../../lib/scoreBands'
import styles from './Results.module.css'

// Plain names for the models the API reports.
const METHODS: Record<string, string> = { 'tfidf-baseline': 'TF-IDF' }

/** The score as a number, its band and a flat meter, with the caveat for an uncalibrated score. */
export function ScoreSummary({ result }: { result: MatchResponse }) {
  const method = METHODS[result.model.name] ?? result.model.name

  // A calibrated score is a percentage of fit; until the model is calibrated the API flags the
  // raw similarity, which only makes sense next to its band.
  if (!result.warnings.includes('uncalibrated_score')) {
    const percent = Math.round(result.score * 100)
    return (
      <div className={styles.block}>
        <p className={styles.label}>Match score · {method}</p>
        <p className={styles.value}>{percent}%</p>
        <meter className={styles.meter} min={0} max={1} value={result.score} aria-hidden="true" />
      </div>
    )
  }

  const value = result.score.toFixed(3)
  const band = scoreBand(result.score)
  return (
    <div className={styles.block}>
      <p className={styles.label}>Text similarity · {method}</p>
      <p className={styles.valueRow}>
        <span className={styles.value}>{value}</span>
        <span className={styles.band}>{band}</span>
      </p>
      <meter
        className={styles.meter}
        min={0}
        max={METER_MAX}
        low={SCORE_BANDS.moderate}
        high={SCORE_BANDS.strong}
        optimum={METER_MAX}
        value={Math.min(result.score, METER_MAX)}
        aria-label={`Text similarity ${value}, ${band.toLowerCase()}`}
      />
      <p className={styles.scale}>
        Low &lt; {SCORE_BANDS.moderate} · Moderate {SCORE_BANDS.moderate}–{SCORE_BANDS.strong} ·
        Strong ≥ {SCORE_BANDS.strong} (provisional)
      </p>
      <p className={styles.caveat}>
        Uncalibrated. Best used to compare several jobs against the same CV.
      </p>
    </div>
  )
}
