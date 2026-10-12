import { useEffect, useState, type FormEvent } from 'react'
import {
  JD_MAX,
  JD_MIN,
  MAX_CV_BYTES,
  matchCv,
  wakeServer,
  type ApiFailure,
  type MatchResponse,
} from './api/client'
import { CvPicker } from './components/CvPicker'
import { Result } from './components/Result'
import { SAMPLE_CV_URL, SAMPLE_JD, loadSampleCv } from './sample'

type Server = 'waking' | 'ready' | 'down'
type Phase =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'done'; result: MatchResponse }
  | { kind: 'failed'; error: ApiFailure }

const REPO_URL = 'https://github.com/kose-labs/p1-resume-job-matcher'

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

  const pickFile = (file: File | null) => {
    const error = file ? checkCvFile(file) : null
    setFileError(error)
    setCv(error ? null : file)
  }

  const fillSample = async () => {
    setJobDescription(SAMPLE_JD)
    const file = await loadSampleCv()
    if (file) pickFile(file)
    else setFileError("Couldn't load the sample CV. Choose a PDF of your own instead.")
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
    <div className="page">
      <header className="hero">
        <p className="brand">KoSe Labs</p>
        <h1>Resume–Job Matcher</h1>
        <p className="lead">
          Paste a job description and upload a CV. Your CV is processed in memory and never stored.
        </p>
        <p role="status" className={`server server-${server}`}>
          <span className="dot" aria-hidden="true" />
          {server === 'waking' && 'Waking up the server… this can take up to a minute.'}
          {server === 'ready' && 'Server ready.'}
          {server === 'down' && (
            <>
              The server isn't answering.{' '}
              <button type="button" className="link" onClick={retry}>
                Try again
              </button>
            </>
          )}
        </p>
      </header>

      <main>
        <form className="card" onSubmit={onSubmit}>
          <div className="card-head">
            <h2>Match a CV to a job</h2>
            <p className="sample">
              No CV handy?{' '}
              <button type="button" className="link" onClick={() => void fillSample()}>
                Use sample data
              </button>{' '}
              (
              <a href={SAMPLE_CV_URL} download>
                sample CV
              </a>
              , fictional)
            </p>
          </div>

          <div className="field">
            <label htmlFor="jd" className="field-label">
              Job description
            </label>
            <textarea
              id="jd"
              rows={10}
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
              aria-describedby="jd-help"
              placeholder="Paste the full job description: requirements, responsibilities, nice-to-haves."
            />
            <small id="jd-help" className="hint">
              {jdLength.toLocaleString()} / {JD_MAX.toLocaleString()} characters
              {jdLength < JD_MIN && ` (at least ${JD_MIN})`}
            </small>
          </div>

          <CvPicker file={cv} error={fileError} onPick={pickFile} />

          <button type="submit" className="primary" disabled={!canSubmit}>
            {phase.kind === 'loading' && <span className="spinner" aria-hidden="true" />}
            {phase.kind === 'loading' ? 'Matching…' : 'Match'}
          </button>

          {phase.kind === 'failed' && (
            <p role="alert" className="error">
              {phase.error.message}
              {phase.error.retryAfterSeconds &&
                ` You can try again in ${phase.error.retryAfterSeconds} seconds.`}
            </p>
          )}
        </form>

        {phase.kind === 'done' && <Result result={phase.result} />}

        <section className="how" aria-labelledby="how-title">
          <h2 id="how-title">How it works</h2>
          <ol>
            <li>
              <strong>Read.</strong> The text of your PDF is extracted in memory. Text-based PDFs
              only: scanned CVs are rejected with a message.
            </li>
            <li>
              <strong>Compare.</strong> The CV is scored against the job description by how much
              their wording overlaps, weighted towards the terms that matter.
            </li>
            <li>
              <strong>Forget.</strong> Nothing is saved: no account, no database, and no CV text in
              our logs.
            </li>
          </ol>
        </section>
      </main>

      <footer>
        <p>
          Built by KoSe Labs · <a href={REPO_URL}>Source on GitHub</a>
        </p>
      </footer>
    </div>
  )
}
