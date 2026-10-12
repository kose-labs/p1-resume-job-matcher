import { useEffect, useRef } from 'react'
import type { MatchResponse } from '../api/client'

/** The match result: score, skills, evidence and the model that produced them. */
export function Result({ result }: { result: MatchResponse }) {
  // An uncalibrated score is a raw similarity, not a probability of fit, so it isn't shown as a
  // percentage ("4% match" would mislead); the bar still lets results be compared at a glance.
  const calibrated = !result.warnings.includes('uncalibrated_score')
  const percent = Math.round(result.score * 100)

  // Move focus to the new result: on a phone it's below the form, and focusing scrolls it into view
  // and tells screen readers it has arrived.
  const section = useRef<HTMLElement>(null)
  useEffect(() => section.current?.focus(), [])

  return (
    <section ref={section} tabIndex={-1} className="card result" aria-label="Match result">
      <div className="score">
        <h2>
          {calibrated ? `Match score: ${percent}%` : `Text similarity: ${result.score.toFixed(2)}`}
        </h2>
        <div className="meter" aria-hidden="true">
          <span style={{ width: `${percent}%` }} />
        </div>
        {!calibrated && (
          <p className="note">
            This is a raw text similarity, not yet calibrated against human ratings, so even strong
            matches score low. Use it to compare jobs for the same CV.
          </p>
        )}
      </div>

      <SkillLists skills={result.skills} />

      {result.evidence.length > 0 && (
        <div className="block">
          <h3>Why this score</h3>
          <ul className="evidence">
            {result.evidence.map((item) => (
              <li key={`${item.requirement}|${item.cv_excerpt}`}>
                <p className="requirement">{item.requirement}</p>
                <p className="excerpt">“{item.cv_excerpt}”</p>
                <p className="similarity">{Math.round(item.similarity * 100)}% similar</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="model">
        Model: {result.model.name} v{result.model.version}
      </p>
    </section>
  )
}

function SkillLists({ skills }: { skills: MatchResponse['skills'] }) {
  // Both lists empty means no skills were recognised in the job description at all (also the case
  // until skill extraction lands): one honest line instead of "None found" next to "None".
  if (!skills.matched.length && !skills.missing.length) {
    return <p className="note block">No specific skills were recognised in this job description.</p>
  }
  return (
    <div className="block skills">
      <div>
        <h3>Skills the CV covers</h3>
        {skills.matched.length ? (
          <ul className="chips matched">
            {skills.matched.map((skill) => (
              <li key={skill.name}>{skill.name}</li>
            ))}
          </ul>
        ) : (
          <p>None found.</p>
        )}
      </div>
      <div>
        <h3>Skills the CV is missing</h3>
        {skills.missing.length ? (
          <ul className="chips missing">
            {skills.missing.map((skill) => (
              <li key={skill.name}>{skill.name}</li>
            ))}
          </ul>
        ) : (
          <p>None.</p>
        )}
      </div>
    </div>
  )
}
