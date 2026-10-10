import { useEffect, useState } from 'react'

type Status = { kind: 'loading' } | { kind: 'ok'; version: string } | { kind: 'error' }

// Relative URL: in dev the Vite proxy forwards /api to the backend;
// in production VITE_API_URL points at the deployed backend.
const API_URL = import.meta.env.VITE_API_URL ?? ''

export default function App() {
  const [status, setStatus] = useState<Status>({ kind: 'loading' })

  useEffect(() => {
    fetch(`${API_URL}/api/v1/version`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<{ version: string }>
      })
      .then((data) => setStatus({ kind: 'ok', version: data.version }))
      .catch(() => setStatus({ kind: 'error' }))
  }, [])

  return (
    <main>
      <h1>KoSe Labs</h1>
      <p>Project template: FastAPI backend + React frontend.</p>
      <p role="status">
        {status.kind === 'loading' && 'Connecting to the backend…'}
        {status.kind === 'ok' && `Backend connected (v${status.version})`}
        {status.kind === 'error' && 'Backend unreachable. Is it running on port 8000?'}
      </p>
    </main>
  )
}
