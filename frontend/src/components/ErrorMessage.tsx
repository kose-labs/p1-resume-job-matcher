import type { ErrorCopy } from '../lib/errors'
import styles from './ErrorMessage.module.css'

/** A failure: what happened, then what to do next. */
export function ErrorMessage({ title, detail }: ErrorCopy) {
  return (
    <div role="alert" className={styles.error}>
      <p className={styles.title}>{title}</p>
      <p className={styles.detail}>{detail}</p>
    </div>
  )
}
