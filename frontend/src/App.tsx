import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react'
import styles from './App.module.css'
import { JD_MAX, JD_MIN, MAX_CV_BYTES, matchCv, wakeServer } from './api/client'
import { AppShell } from './components/AppShell'
import { CvDropzone } from './components/CvDropzone'
import { JobDescriptionInput } from './components/JobDescriptionInput'
import { MatchResults, type Phase } from './components/MatchResults/MatchResults'
import { SiteFooter } from './components/SiteFooter'
import { TopBar, type Server } from './components/TopBar'
import { useTheme } from './lib/theme'
import { SAMPLE_JD, loadSampleCv } from './sample'
import controls from './styles/controls.module.css'

/** Return a message if the file can't be sent, or null if it looks fine. */
function checkCvFile(file: File): string | null {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  if (!isPdf) return 'This file is not a PDF. Export the CV as a PDF and choose it again.'
  if (file.size > MAX_CV_BYTES) return 'This file is over 5 MB. Export a smaller PDF and try again.'
  return null
}

/** What's wrong with the job description's length, or null if it's fine. */
function jobDescriptionProblem(length: number): string | null {
  if (length === 0) return `Add a job description of at least ${JD_MIN} characters.`
  if (length < JD_MIN) return `Add at least ${JD_MIN - length} more characters.`
  if (length > JD_MAX)
    return `Shorten the job description to ${JD_MAX.toLocaleString()} characters.`
  return null
}

const SHORTCUT = /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⌘ Enter' : 'Ctrl Enter'

export default function App() {
  const [theme, setTheme] = useTheme()
  const [server, setServer] = useState<Server>('waking')
  const [apiVersion, setApiVersion] = useState<string | null>(null)
  const [jobDescription, setJobDescription] = useState('')
  const [cv, setCv] = useState<File | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  // Field errors only show once someone tries to run with an incomplete form.
  const [attempted, setAttempted] = useState(false)
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })

  // The page starts in 'waking', so the effect only updates state once the server answers.
  const checkServer = () =>
    wakeServer().then((version) => {
      setApiVersion(version)
      setServer(version ? 'ready' : 'down')
    })
  useEffect(() => {
    void checkServer()
  }, [])
  const retry = () => {
    setServer('waking')
    void checkServer()
  }

  const jdProblem = jobDescriptionProblem(jobDescription.trim().length)
  const valid = jdProblem === null && cv !== null
  const running = phase.kind === 'loading'

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

  const run = async () => {
    if (running) return
    if (!valid || cv === null) {
      setAttempted(true)
      return
    }
    setPhase({ kind: 'loading' })
    const outcome = await matchCv(cv, jobDescription)
    setPhase(
      outcome.ok
        ? { kind: 'done', result: outcome.data, elapsedMs: outcome.elapsedMs }
        : { kind: 'failed', error: outcome.error },
    )
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void run()
  }
  const onKeyDown = (event: KeyboardEvent<HTMLFormElement>) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      void run()
    }
  }

  const inputs = (
    <form className={styles.form} onSubmit={onSubmit} onKeyDown={onKeyDown} noValidate>
      <JobDescriptionInput
        value={jobDescription}
        onChange={setJobDescription}
        error={attempted ? jdProblem : null}
      />
      <CvDropzone
        file={cv}
        error={fileError ?? (attempted && cv === null ? 'Choose the CV as a PDF.' : null)}
        onPick={pickFile}
      />
      <div className={styles.actions}>
        <button type="button" className={controls.textButton} onClick={() => void fillSample()}>
          Use sample data
        </button>
        <div className={styles.run}>
          <kbd className={controls.kbd} aria-hidden="true">
            {SHORTCUT}
          </kbd>
          <button
            type="submit"
            className={controls.primary}
            disabled={!valid}
            // While running it stays focusable (aria-disabled, not disabled), so keyboard focus
            // isn't dropped to the top of the page; run() ignores presses until the result arrives.
            aria-disabled={running}
            aria-keyshortcuts="Control+Enter Meta+Enter"
          >
            {running && <span className={controls.spinner} aria-hidden="true" />}
            {running ? 'Running…' : 'Run match'}
          </button>
        </div>
      </div>
    </form>
  )

  return (
    <AppShell
      topBar={
        <TopBar
          apiVersion={apiVersion}
          server={server}
          onRetry={retry}
          theme={theme}
          onThemeChange={setTheme}
        />
      }
      inputs={inputs}
      results={<MatchResults phase={phase} />}
      footer={<SiteFooter />}
    />
  )
}
