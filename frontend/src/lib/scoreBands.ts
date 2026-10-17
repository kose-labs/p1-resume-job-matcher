/**
 * Plain-language bands for the TF-IDF score (ADR-0006), so a raw number like 0.043 reads as Low,
 * Moderate or Strong. Fitted on our dev ratings (2026-10-16, 40 pairs from 10 JDs, the mean of two
 * raters): Strong where we rated a pair 4 or more on average, Low at 2 or less. These thresholds
 * put 27 of the 40 pairs in the right band, against 20 for the earlier ones (0.03 and 0.06, set
 * from score quantiles before any rating). Checked once on test (model card).
 */
export const SCORE_BANDS = { moderate: 0.04, strong: 0.055 } as const

/**
 * The curve from a raw score to an estimated fit from 0 to 100%: how we'd likely rate the pair,
 * with rating 1 at 0% and rating 5 at 100%. A logistic in ln(score), fitted on the same 40 dev pairs
 * (`scripts/j2-pairs/evaluate.py calibrate`, app.ml.calibration). It lands 0.76 rating points from
 * our ratings on JDs it wasn't fitted on, against 1.08 for always guessing the average. The curve
 * only rises, so it never changes which of two pairs ranks higher.
 */
export const FIT_CURVE = { a: 5.2912, b: 1.6983 } as const

/** Estimated fit from 0 to 1 for a raw TF-IDF score. */
export function fitPercent(score: number): number {
  const z = FIT_CURVE.a + FIT_CURVE.b * Math.log(Math.max(score, 1e-6))
  return 1 / (1 + Math.exp(-z))
}

/** The band thresholds on the fit scale, as whole percentages (46 and 59). */
export const FIT_BANDS = {
  moderate: Math.round(fitPercent(SCORE_BANDS.moderate) * 100),
  strong: Math.round(fitPercent(SCORE_BANDS.strong) * 100),
} as const

export type Band = 'Low' | 'Moderate' | 'Strong'

export function scoreBand(score: number): Band {
  if (score >= SCORE_BANDS.strong) return 'Strong'
  if (score >= SCORE_BANDS.moderate) return 'Moderate'
  return 'Low'
}
