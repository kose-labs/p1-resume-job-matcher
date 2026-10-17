import styles from './Intro.module.css'
import { StepNumber } from './StepNumber'

const STEPS = ['Paste a job description', 'Add the CV as a PDF', 'Run the match']

/** What the page does, in one line and three steps, with the privacy promise up front. */
export function Intro() {
  return (
    <section className={styles.intro} aria-labelledby="intro-title">
      <div className={styles.inner}>
        <h2 id="intro-title" className={styles.headline}>
          See how well a CV fits a job, and which of its skills the CV is missing.
        </h2>
        <ol className={styles.steps}>
          {STEPS.map((step, i) => (
            <li key={step} className={styles.step}>
              <StepNumber n={i + 1} />
              {step}
            </li>
          ))}
        </ol>
        <p className={styles.privacy}>
          <svg
            className={styles.lock}
            viewBox="0 0 16 16"
            width="14"
            height="14"
            aria-hidden="true"
          >
            <rect x="3" y="7" width="10" height="7" rx="1.5" />
            <path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" />
          </svg>
          Your CV is read in memory and never stored.
        </p>
      </div>
    </section>
  )
}
