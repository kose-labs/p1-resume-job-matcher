import { useEffect, useRef } from 'react'
import type { ApiFailure, MatchResponse } from '../../api/client'
import { describeFailure } from '../../lib/errors'
import { EmptyState } from '../EmptyState'
import { ErrorMessage } from '../ErrorMessage'
import { EvidenceList } from './EvidenceList'
import { ResultMeta } from './ResultMeta'
import { ResultsSkeleton } from './ResultsSkeleton'
import { ScoreSummary } from './ScoreSummary'
import { SkillsBreakdown } from './SkillsBreakdown'
import styles from './Results.module.css'

export type Phase =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'done'; result: MatchResponse; elapsedMs: number }
  | { kind: 'failed'; error: ApiFailure }

/** The results pane in each state: nothing run yet, running, a result, or a failure. */
export function MatchResults({ phase }: { phase: Phase }) {
  const region = useRef<HTMLDivElement>(null)

  // On a phone the results sit below the form: bring a new result or error into view. On a wide
  // screen the pane is already visible beside the form, so nothing moves.
  useEffect(() => {
    const el = region.current
    if ((phase.kind === 'done' || phase.kind === 'failed') && el) {
      if (el.getBoundingClientRect().top > window.innerHeight) el.scrollIntoView()
    }
  }, [phase])

  return (
    // aria-live: screen readers announce results and errors when they appear.
    <div ref={region} aria-live="polite" aria-busy={phase.kind === 'loading'}>
      {phase.kind === 'idle' && <EmptyState />}
      {phase.kind === 'loading' && <ResultsSkeleton />}
      {phase.kind === 'failed' && <ErrorMessage {...describeFailure(phase.error)} />}
      {phase.kind === 'done' && (
        <div className={styles.report}>
          <ScoreSummary result={phase.result} />
          <SkillsBreakdown skills={phase.result.skills} />
          {phase.result.evidence.length > 0 && <EvidenceList evidence={phase.result.evidence} />}
          <ResultMeta model={phase.result.model} elapsedMs={phase.elapsedMs} />
        </div>
      )}
    </div>
  )
}
