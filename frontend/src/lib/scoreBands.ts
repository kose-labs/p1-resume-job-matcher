/**
 * Provisional reading of the uncalibrated TF-IDF score (ADR-0006), so a raw number like 0.043 has
 * a plain-language band. Set from the deployed model's scores on the 900 pairs of our evaluation
 * corpus (2026-10-13): three quarters of unrelated pairs score below 0.03, and the top quarter of
 * same-field pairs score 0.06 or more. To be replaced by thresholds fitted to our ratings (J2).
 */
export const SCORE_BANDS = { moderate: 0.03, strong: 0.06 } as const

/** Full scale of the score meter: about the highest score a real CV–job pair reached (0.132). */
export const METER_MAX = 0.12

export type Band = 'Low' | 'Moderate' | 'Strong'

export function scoreBand(score: number): Band {
  if (score >= SCORE_BANDS.strong) return 'Strong'
  if (score >= SCORE_BANDS.moderate) return 'Moderate'
  return 'Low'
}
