import type { MatchResponse } from '../../api/client'
import styles from './Results.module.css'

/** Job requirements paired with the CV sentence that covers each best, strongest first. */
export function EvidenceList({ evidence }: { evidence: MatchResponse['evidence'] }) {
  return (
    <div className={styles.block}>
      <h3 className={styles.heading}>Evidence</h3>
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
