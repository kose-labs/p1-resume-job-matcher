import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  JD_MAX,
  JD_MIN,
  MAX_CV_BYTES,
  matchCv,
  wakeServer,
  type ApiFailure,
  type MatchResponse,
} from './api/client'

type Server = 'waking' | 'ready' | 'down'
type Phase =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'done'; result: MatchResponse }
  | { kind: 'failed'; error: ApiFailure }

/** Return a message if the file can't be sent, or null if it looks fine. */
function checkCvFile(file: File): string | null {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) return 'The CV must be a PDF file.'
  if (file.size > MAX_CV_BYTES) return 'The CV must be 5 MB or smaller.'
  return null
}

export default function App() {
  const [server, setServer] = useState<Server>('waking')
  const [jobDescription, setJobDescription] = useState('')
  const [cv, setCv] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })

  // The page starts in 'waking', so the effect only updates state once the server answers.
  const checkServer = () => wakeServer().then((ok) => setServer(ok ? 'ready' : 'down'))
  useEffect(() => {
    void checkServer()
  }, [])
  const retry = () => {
    setServer('waking')
    void checkServer()
  }

  const jdLength = jobDescription.trim().length
  const jdValid = jdLength >= JD_MIN && jdLength <= JD_MAX
  const canSubmit = jdValid && cv !== null && phase.kind !== 'loading'

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    const error = file ? checkCvFile(file) : null
    setFileError(error)
    setCv(error ? null : file)
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!cv) return
    setPhase({ kind: 'loading' })
    const outcome = await matchCv(cv, jobDescription)
    setPhase(
      outcome.ok
        ? { kind: 'done', result: outcome.data }
        : { kind: 'failed', error: outcome.error },
    )
  }

  return (
    <main>
      <h1>Resume–Job Matcher</h1>
      <p>
        Paste a job description and upload a CV. Your CV is processed in memory and never stored.
      </p>

      <p role="status" className={`server server-${server}`}>
        {server === 'waking' && 'Waking up the server… this can take up to a minute.'}
        {server === 'ready' && 'Server ready.'}
        {server === 'down' && (
          <>
            The server isn't answering.{' '}
            <button type="button" onClick={retry}>
              Try again
            </button>
          </>
        )}
      </p>

      <form onSubmit={onSubmit}>
        <label htmlFor="jd">Job description</label>
        <textarea
          id="jd"
          rows={10}
          value={jobDescription}
          onChange={(event) => setJobDescription(event.target.value)}
          aria-describedby="jd-help"
        />
        <small id="jd-help">
          {jdLength.toLocaleString()} / {JD_MAX.toLocaleString()} characters
          {jdLength < JD_MIN && ` (at least ${JD_MIN})`}
        </small>

        <label htmlFor="cv">CV (PDF, up to 5 MB)</label>
        <input id="cv" type="file" accept="application/pdf,.pdf" onChange={onFileChange} />
        {fileError && <p role="alert">{fileError}</p>}

        <button type="submit" disabled={!canSubmit}>
          {phase.kind === 'loading' ? 'Matching…' : 'Match'}
        </button>
      </form>

      {phase.kind === 'failed' && (
        <p role="alert">
          {phase.error.message}
          {phase.error.retryAfterSeconds &&
            ` You can try again in ${phase.error.retryAfterSeconds} seconds.`}
        </p>
      )}
      {phase.kind === 'done' && <Result result={phase.result} />}
    </main>
  )
}

function Result({ result }: { result: MatchResponse }) {
  return (
    <section aria-label="Match result">
      <h2>Match score: {Math.round(result.score * 100)}%</h2>
      {result.warnings.includes('stub_model') && (
        <p className="note">
          The matching model isn't connected yet, so this is a placeholder result.
        </p>
      )}

      <h3>Skills the CV covers</h3>
      {result.skills.matched.length ? (
        <ul>
          {result.skills.matched.map((skill) => (
            <li key={skill.name}>{skill.name}</li>
          ))}
        </ul>
      ) : (
        <p>None found.</p>
      )}

      <h3>Skills the CV is missing</h3>
      {result.skills.missing.length ? (
        <ul>
          {result.skills.missing.map((skill) => (
            <li key={skill.name}>{skill.name}</li>
          ))}
        </ul>
      ) : (
        <p>None.</p>
      )}

      {result.evidence.length > 0 && (
        <>
          <h3>Why this score</h3>
          <ul>
            {result.evidence.map((item) => (
              <li key={`${item.requirement}|${item.cv_excerpt}`}>
                <strong>{item.requirement}</strong> ↔ “{item.cv_excerpt}” (
                {Math.round(item.similarity * 100)}%)
              </li>
            ))}
          </ul>
        </>
      )}

      <p className="model">
        Model: {result.model.name} v{result.model.version}
      </p>
    </section>
  )
}
