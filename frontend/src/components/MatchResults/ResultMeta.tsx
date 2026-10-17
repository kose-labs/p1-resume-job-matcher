import { useEffect, useState } from 'react'
import type { MatchResponse } from '../../api/client'
import { resultSummary } from '../../lib/summary'
import controls from '../../styles/controls.module.css'
import styles from './Results.module.css'

type Props = { result: MatchResponse; elapsedMs: number }

/** Which model produced the result and how long the request took, with a button that copies a
 * text summary (shown only where the browser allows writing to the clipboard). */
export function ResultMeta({ result, elapsedMs }: Props) {
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    if (!copied) return
    const timer = setTimeout(() => setCopied(false), 2000)
    return () => clearTimeout(timer)
  }, [copied])

  const copy = () =>
    navigator.clipboard.writeText(resultSummary(result)).then(
      () => setCopied(true),
      () => setCopied(false),
    )

  return (
    <div className={styles.metaRow}>
      <p className={styles.meta}>
        {result.model.name} {result.model.version} · {elapsedMs.toLocaleString()} ms round trip
      </p>
      {'clipboard' in navigator && (
        <button type="button" className={controls.textButton} onClick={() => void copy()}>
          {copied ? 'Copied' : 'Copy results'}
        </button>
      )}
    </div>
  )
}
