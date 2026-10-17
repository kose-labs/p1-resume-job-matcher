import { JD_MAX, JD_MIN } from '../api/client'
import styles from './Field.module.css'
import { StepNumber } from './StepNumber'

type Props = {
  value: string
  onChange: (value: string) => void
  error: string | null
}

/** The job description box, with a live character count and the length rule. */
export function JobDescriptionInput({ value, onChange, error }: Props) {
  const length = value.trim().length
  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <StepNumber n={1} />
        <label htmlFor="jd" className={styles.label}>
          Job description
        </label>
      </div>
      <textarea
        id="jd"
        className={styles.textarea}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-describedby="jd-help jd-count"
        aria-invalid={error !== null}
        placeholder="Paste the full job description, including requirements and responsibilities."
      />
      <div className={styles.meta}>
        {error ? (
          <p id="jd-help" role="alert" className={styles.error}>
            {error}
          </p>
        ) : (
          <p id="jd-help" className={styles.hint}>
            {length < JD_MIN ? `At least ${JD_MIN} characters` : ''}
          </p>
        )}
        <p id="jd-count" className={styles.count}>
          {length.toLocaleString()} / {JD_MAX.toLocaleString()}
        </p>
      </div>
    </div>
  )
}
