/**
 * Plain-language bands for the uncalibrated TF-IDF score (ADR-0006), so a raw number like 0.043
 * reads as Low, Moderate or Strong. Fitted on our dev ratings (2026-10-16, 40 pairs from 10 JDs,
 * the mean of two raters): Strong where we rated a pair 4 or more on average, Low at 2 or less.
 * These thresholds put 27 of the 40 pairs in the right band, against 20 for the earlier ones
 * (0.03 and 0.06, set from score quantiles before any rating). Checked once on test (model card).
 */
export const SCORE_BANDS = { moderate: 0.04, strong: 0.055 } as const

/** Full scale of the score meter: about the highest score a real CV–job pair reached (0.132). */
export const METER_MAX = 0.12

export type Band = 'Low' | 'Moderate' | 'Strong'

export function scoreBand(score: number): Band {
  if (score >= SCORE_BANDS.strong) return 'Strong'
  if (score >= SCORE_BANDS.moderate) return 'Moderate'
  return 'Low'
}
