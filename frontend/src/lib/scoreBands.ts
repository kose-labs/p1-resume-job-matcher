/**
 * The curve from a raw score to an estimated fit from 0 to 100%: how we'd likely rate the pair,
 * with rating 1 at 0% and rating 5 at 100%. A logistic in ln(score), fitted on our 40 dev pairs
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

/** The fit is shown in steps of this many percent. */
export const FIT_STEP = 5

/**
 * The fit as shown: rounded to the nearest 5%. Its typical error is about ±19 points (0.76 rating
 * points), so a single percent would suggest a precision it doesn't have.
 */
export function shownFit(score: number): number {
  return Math.round((fitPercent(score) * 100) / FIT_STEP) * FIT_STEP
}

/**
 * Plain-language bands on the shown fit, so the band never contradicts the percentage next to it:
 * Low up to 40%, Moderate 45–55%, Strong from 60% (raw scores of about 0.037 and 0.053). Fitted on
 * our dev ratings (2026-10-16, 40 pairs from 10 JDs, the mean of two raters): Strong where we rated
 * a pair 4 or more on average, Low at 2 or less. They put 27 of the 40 pairs in the right band, the
 * same as the raw thresholds they replace (0.04 and 0.055) and against 20 for the first ones (0.03
 * and 0.06, set from score quantiles before any rating). Checked once on test (model card).
 */
export const FIT_BANDS = { moderate: 45, strong: 60 } as const

export type Band = 'Low' | 'Moderate' | 'Strong'

export function scoreBand(score: number): Band {
  const fit = shownFit(score)
  if (fit >= FIT_BANDS.strong) return 'Strong'
  if (fit >= FIT_BANDS.moderate) return 'Moderate'
  return 'Low'
}
