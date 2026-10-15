import type { MatchResponse } from '../../api/client'
import styles from './Results.module.css'

type Props = { model: MatchResponse['model']; elapsedMs: number }

/** Which model produced the result, and how long the request took. */
export function ResultMeta({ model, elapsedMs }: Props) {
  return (
    <p className={styles.meta}>
      {model.name} {model.version} · {elapsedMs.toLocaleString()} ms round trip
    </p>
  )
}
