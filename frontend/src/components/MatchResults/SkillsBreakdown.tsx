import type { MatchResponse } from '../../api/client'
import styles from './Results.module.css'

type Skill = MatchResponse['skills']['matched'][number]

/** Skills from the job description: how many the CV covers, then those it names and those it
 * doesn't, with a tip for the missing ones. */
export function SkillsBreakdown({ skills }: { skills: MatchResponse['skills'] }) {
  const total = skills.matched.length + skills.missing.length
  if (total === 0) {
    return (
      <div className={styles.block}>
        <h3 className={styles.heading}>Skills</h3>
        <p className={styles.muted}>No skills were identified in this job description.</p>
      </div>
    )
  }
  const share = Math.round((skills.matched.length / total) * 100)
  return (
    <div className={styles.block}>
      <h3 className={styles.heading}>Skills</h3>
      <p className={styles.coverage}>
        The CV names <strong>{skills.matched.length}</strong> of the job&apos;s{' '}
        <strong>{total}</strong> skills
      </p>
      <div className={styles.coverageBar} aria-hidden="true">
        <span style={{ width: `${share}%` }} />
      </div>
      <div className={styles.columns}>
        <SkillColumn title="Matched in CV" kind="matched" skills={skills.matched} />
        <SkillColumn title="Missing from CV" kind="missing" skills={skills.missing} />
      </div>
      {skills.missing.length > 0 && (
        <p className={styles.tip}>
          Have any of the missing skills? Name them in the CV: the matcher only counts what&apos;s
          written.
        </p>
      )}
    </div>
  )
}

function SkillColumn({ title, kind, skills }: { title: string; kind: string; skills: Skill[] }) {
  return (
    <div>
      <p className={styles.columnTitle}>
        <span className={styles.dot} data-kind={kind} aria-hidden="true" />
        {title}
        <span className={styles.count}>{skills.length}</span>
      </p>
      {skills.length ? (
        <ul className={styles.tags}>
          {skills.map((skill) => (
            <li key={skill.name} className={styles.tag} data-kind={kind}>
              {skill.name}
            </li>
          ))}
        </ul>
      ) : (
        <p className={styles.muted}>None</p>
      )}
    </div>
  )
}
