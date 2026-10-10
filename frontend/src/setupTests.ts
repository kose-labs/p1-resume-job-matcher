import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Vitest runs without globals here, so Testing Library can't clean up on its own:
// unmount each test's components so the next test starts with an empty page.
afterEach(cleanup)
