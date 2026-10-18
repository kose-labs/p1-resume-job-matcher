import styles from './StepNumber.module.css'

/** A step's number in a small circle; decorative, since the text around it says the step. */
export function StepNumber({ n }: { n: number }) {
  return (
    <span className={styles.number} aria-hidden="true">
      {n}
    </span>
  )
}
