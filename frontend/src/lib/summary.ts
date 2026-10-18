import type { MatchResponse } from '../api/client'
import { scoreBand, shownFit } from './scoreBands'

/** A plain-text summary of a result, for pasting into notes or a message. */
export function resultSummary(result: MatchResponse): string {
  const score = result.warnings.includes('uncalibrated_score')
    ? `${scoreBand(result.score)} fit (estimated fit ≈ ${shownFit(result.score)}%, raw similarity ${result.score.toFixed(3)})`
    : `Match score ${Math.round(result.score * 100)}%`
  const { matched, missing } = result.skills
  const names = (skills: typeof matched) => skills.map((skill) => skill.name).join(', ') || 'none'
  return [
    'Resume–Job Matcher (KoSe Labs)',
    score,
    `Skills the CV names (${matched.length} of ${matched.length + missing.length}): ${names(matched)}`,
    `Missing from the CV: ${names(missing)}`,
    `Model: ${result.model.name} ${result.model.version}`,
  ].join('\n')
}
