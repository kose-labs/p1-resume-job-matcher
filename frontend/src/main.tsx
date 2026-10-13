import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Self-hosted fonts (Latin subset only): loading them from a font CDN would send every visitor's
// IP address to a third party, which our privacy promise rules out.
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-500.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import './styles/tokens.css'
import './styles/base.css'
import App from './App.tsx'
import { applyTheme, readTheme } from './lib/theme'

// Before the first render, so a saved theme doesn't flash the other one.
applyTheme(readTheme())

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
