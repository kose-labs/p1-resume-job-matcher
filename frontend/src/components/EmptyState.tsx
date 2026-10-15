import styles from './MatchResults/Results.module.css'

/** What the results pane says before the first match. */
export function EmptyState() {
  return (
    <p className={styles.muted}>
      Run a match to see the similarity score, the skills found in both texts, and the model used.
    </p>
  )
}
