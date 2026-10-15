import type { MatchResponse } from '../../api/client'
import styles from './Results.module.css'

type Skill = MatchResponse['skills']['matched'][number]

/** Skills from the job description, split into those the CV covers and those it doesn't. */
export function SkillsBreakdown({ skills }: { skills: MatchResponse['skills'] }) {
  const none = skills.matched.length === 0 && skills.missing.length === 0
  return (
    <div className={styles.block}>
      <h3 className={styles.heading}>Skills</h3>
      {none ? (
        <p className={styles.muted}>No skills were identified in this job description.</p>
      ) : (
        <div className={styles.columns}>
          <SkillColumn title="Matched in CV" kind="matched" skills={skills.matched} />
          <SkillColumn title="Missing from CV" kind="missing" skills={skills.missing} />
        </div>
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
            <li key={skill.name} className={styles.tag}>
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
