import type { MatchResponse } from '../../api/client'
import styles from './Results.module.css'

type Props = { evidence: MatchResponse['evidence']; truncated: boolean }

/** Job requirements paired with the CV sentence that backs each up, strongest first. */
export function EvidenceList({ evidence, truncated }: Props) {
  return (
    <div className={styles.block}>
      <h3 className={styles.heading}>Evidence</h3>
      <p className={styles.muted}>
        CV sentences that name a skill a requirement asks for, ranked by shared terms.
        {truncated && ' This CV is long, so only its first part (about 4 pages) was searched.'}
      </p>
      <ol className={styles.evidence}>
        {evidence.map((item) => (
          <li key={`${item.requirement}|${item.cv_excerpt}`} className={styles.evidenceItem}>
            <p className={styles.requirement}>{item.requirement}</p>
            <p className={styles.similarity}>{item.similarity.toFixed(2)}</p>
            <p className={styles.excerpt}>{item.cv_excerpt}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}
