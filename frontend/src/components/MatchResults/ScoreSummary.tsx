import type { MatchResponse } from '../../api/client'
import {
  FIT_BANDS,
  FIT_STEP,
  fitPercent,
  scoreBand,
  shownFit,
  type Band,
} from '../../lib/scoreBands'
import styles from './Results.module.css'

// Plain names for the models the API reports.
const METHODS: Record<string, string> = { 'tfidf-baseline': 'TF-IDF' }

// What each band means, in terms of what the score measures: shared wording and skills.
const VERDICTS: Record<Band, string> = {
  Strong: "The CV shares much of this job's distinctive wording and skills.",
  Moderate: 'The CV covers part of what this job asks for.',
  Low: 'The CV and this job have little in common.',
}

/** The band first with what it means, the fit rounded to 5%, a meter in the band's colour, the
 * scale with the raw similarity, and a caveat. */
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

  const fit = shownFit(result.score)
  const band = scoreBand(result.score)
  return (
    <div className={`${styles.block} ${styles.scoreCard}`} data-band={band.toLowerCase()}>
      <p className={styles.label}>Estimated fit · {method}</p>
      <p className={styles.valueRow}>
        <span className={styles.verdict}>{band} fit</span>
        <span className={styles.band}>≈ {fit}%</span>
      </p>
      <p className={styles.summary}>{VERDICTS[band]}</p>
      <meter
        className={styles.meter}
        min={0}
        max={100}
        // The exact fit where the rounded one reaches each band.
        low={FIT_BANDS.moderate - FIT_STEP / 2}
        high={FIT_BANDS.strong - FIT_STEP / 2}
        optimum={100}
        value={Math.round(fitPercent(result.score) * 100)}
        aria-label={`${band} fit, about ${fit}%`}
      />
      <p className={styles.scale}>
        Low ≤ {FIT_BANDS.moderate - FIT_STEP}% · Moderate {FIT_BANDS.moderate}–
        {FIT_BANDS.strong - FIT_STEP}% · Strong ≥ {FIT_BANDS.strong}% · raw similarity{' '}
        {result.score.toFixed(3)}
      </p>
      <p className={styles.caveat}>
        How we&apos;d likely rate this pair, learned from 40 CV–job pairs we rated by hand. Not a
        probability of being hired: best used to compare several jobs against the same CV.
      </p>
    </div>
  )
}
