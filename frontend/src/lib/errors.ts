import type { ApiFailure } from '../api/client'

/** What the page shows for a failure: what happened, and what to do next. */
export type ErrorCopy = { title: string; detail: string }

// The API's own messages already say what to do (e.g. "export the PDF again"), so they become the
// detail line under a short title.
const TITLES: Record<string, string> = {
  pdf_no_text: 'This PDF looks scanned',
  pdf_unreadable: "This PDF can't be read",
  pdf_too_many_pages: 'This CV is too long',
  unsupported_file_type: 'This file is not a PDF',
  file_too_large: 'This file is over 5 MB',
  invalid_input: 'Check the job description and the CV',
}

export function describeFailure(error: ApiFailure): ErrorCopy {
  switch (error.code) {
    case 'rate_limited':
      return {
        title: 'Too many matches in a short time',
        detail: error.retryAfterSeconds
          ? `Wait ${error.retryAfterSeconds} seconds, then run the match again.`
          : 'Wait a minute, then run the match again.',
      }
    case 'timeout':
      return {
        title: 'The server took too long to answer',
        detail:
          'It may have been starting up after a quiet period. Run the match again; once the server is awake it answers in about a second.',
      }
    case 'network_error':
      return {
        title: "Can't reach the server",
        detail: 'Check your internet connection, then run the match again.',
      }
    default:
      return { title: TITLES[error.code] ?? 'Something went wrong', detail: error.message }
  }
}
