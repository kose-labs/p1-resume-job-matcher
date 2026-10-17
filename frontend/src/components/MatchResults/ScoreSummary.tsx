import type { MatchResponse } from '../../api/client'
import { FIT_BANDS, fitPercent, scoreBand } from '../../lib/scoreBands'
import styles from './Results.module.css'

// Plain names for the models the API reports.
const METHODS: Record<string, string> = { 'tfidf-baseline': 'TF-IDF' }

/** The score as an estimated fit, its band and a flat meter, with the raw similarity and a caveat. */
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

  const fit = Math.round(fitPercent(result.score) * 100)
  const band = scoreBand(result.score)
  return (
    <div className={styles.block}>
      <p className={styles.label}>Estimated fit · {method}</p>
      <p className={styles.valueRow}>
        <span className={styles.value}>{fit}%</span>
        <span className={styles.band}>{band}</span>
      </p>
      <meter
        className={styles.meter}
        min={0}
        max={100}
        low={FIT_BANDS.moderate}
        high={FIT_BANDS.strong}
        optimum={100}
        value={fit}
        aria-label={`Estimated fit ${fit}%, ${band.toLowerCase()}`}
      />
      <p className={styles.scale}>
        Low &lt; {FIT_BANDS.moderate}% · Moderate {FIT_BANDS.moderate}–{FIT_BANDS.strong}% · Strong
        ≥ {FIT_BANDS.strong}% · raw similarity {result.score.toFixed(3)}
      </p>
      <p className={styles.caveat}>
        How we&apos;d likely rate this pair, learned from 40 CV–job pairs we rated by hand. Not a
        probability of being hired: best used to compare several jobs against the same CV.
      </p>
    </div>
  )
}
