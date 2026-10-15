import { useRef, useState, type DragEvent } from 'react'
import controls from '../styles/controls.module.css'
import field from './Field.module.css'
import styles from './CvDropzone.module.css'

type Props = {
  file: File | null
  error: string | null
  onPick: (file: File | null) => void
}

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** A compact row to choose or drop the CV, showing the chosen file with Replace and Remove. */
export function CvDropzone({ file, error, onPick }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const choose = () => input.current?.click()
  const remove = () => {
    // Reset the input too, so choosing the same file again still fires a change. The input is
    // always mounted while this button is.
    input.current!.value = ''
    onPick(null)
  }
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    onPick(event.dataTransfer.files[0] ?? null)
  }

  return (
    <div className={field.field}>
      <label htmlFor="cv" className={field.label}>
        CV <span className={field.labelHint}>PDF, up to 5 MB</span>
      </label>
      {/* Reached through the Choose / Replace buttons, so it stays out of the tab order. */}
      <input
        ref={input}
        id="cv"
        type="file"
        accept="application/pdf,.pdf"
        className="visually-hidden"
        tabIndex={-1}
        aria-invalid={error !== null}
        aria-describedby={error ? 'cv-error' : undefined}
        onChange={(event) => onPick(event.target.files?.[0] ?? null)}
      />
      <div
        className={styles.zone}
        data-dragging={dragging}
        data-has-file={file !== null}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        {file ? (
          <>
            <span className={styles.name}>{file.name}</span>
            <span className={styles.size}>{formatSize(file.size)}</span>
            <span className={styles.actions}>
              <button type="button" className={controls.textButton} onClick={choose}>
                Replace
              </button>
              <button type="button" className={controls.textButton} onClick={remove}>
                Remove
              </button>
            </span>
          </>
        ) : (
          <>
            <span className={styles.prompt}>Drop a PDF here, or</span>
            <button type="button" className={controls.textButton} onClick={choose}>
              choose a file
            </button>
          </>
        )}
      </div>
      {error && (
        <p id="cv-error" role="alert" className={field.error}>
          {error}
        </p>
      )}
    </div>
  )
}
