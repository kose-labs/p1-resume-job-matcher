import styles from './Results.module.css'

/** Placeholder blocks in the shape of a result while the match runs. */
export function ResultsSkeleton() {
  return (
    <div className={styles.report}>
      <p className="visually-hidden">Running the match…</p>
      <div className={styles.block} aria-hidden="true">
        <span className={styles.skeletonLine} data-width="short" />
        <span className={styles.skeletonValue} />
        <span className={styles.skeletonLine} data-width="full" />
      </div>
      <div className={styles.block} aria-hidden="true">
        <span className={styles.skeletonLine} data-width="short" />
        <span className={styles.skeletonLine} data-width="half" />
      </div>
    </div>
  )
}
