// Demo data, so a visitor can try the matcher in a few seconds without a CV of their own: a made-up
// job description and the fictional "Jordan Example" CV that the backend tests also use.

export const SAMPLE_JD = `Backend Engineer (Python)

We're looking for a backend engineer to build and run the APIs behind our product.

Requirements
- 3+ years building REST APIs in Python, with FastAPI or Django
- PostgreSQL: schema design and query tuning
- Docker and CI/CD pipelines
- Writing unit tests and reviewing code

Nice to have
- Go or Node.js
- Cloud hosting on AWS or GCP`

export const SAMPLE_CV_URL = `${import.meta.env.BASE_URL}sample-cv.pdf`

/** Fetch the sample CV as a File, or null if it can't be loaded. */
export async function loadSampleCv(): Promise<File | null> {
  try {
    const response = await fetch(SAMPLE_CV_URL)
    if (!response.ok) return null
    return new File([await response.blob()], 'sample-cv.pdf', { type: 'application/pdf' })
  } catch {
    return null
  }
}
