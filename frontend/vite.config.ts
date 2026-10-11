/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev without Docker: forward API calls to the FastAPI backend.
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text'],
      include: ['src/**/*.{ts,tsx}'],
      // Entry point and test setup only wire things together; there is no logic to test.
      exclude: ['src/main.tsx', 'src/setupTests.ts', 'src/**/*.test.{ts,tsx}'],
      // Floor, not target: raise it as the project grows, never lower it to make CI pass.
      thresholds: { lines: 80, functions: 80, branches: 80, statements: 80 },
    },
  },
})
