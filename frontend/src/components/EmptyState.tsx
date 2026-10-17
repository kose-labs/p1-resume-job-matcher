import styles from './MatchResults/Results.module.css'

const PREVIEW = [
  ['An estimated fit', 'from Low to Strong, learned from CV–job pairs we rated by hand.'],
  ['Skills', 'the job asks for, split into those the CV names and those it misses.'],
  ['Private by design:', 'the CV is read in memory and never stored.'],
]

/** What the results pane shows before the first match: what a result will contain. */
export function EmptyState() {
  return (
    <div className={styles.empty}>
      <p className={styles.emptyTitle}>Your result will appear here</p>
      <ul className={styles.preview}>
        {PREVIEW.map(([lead, rest]) => (
          <li key={lead}>
            <strong>{lead}</strong> {rest}
          </li>
        ))}
      </ul>
      <p className={styles.muted}>No CV to hand? Choose Use sample data.</p>
    </div>
  )
}
