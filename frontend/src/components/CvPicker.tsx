import { useState, type DragEvent } from 'react'

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

/** A file input styled as a drop zone: click to choose a PDF, or drag one onto it. */
export function CvPicker({ file, error, onPick }: Props) {
  const [dragging, setDragging] = useState(false)

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    setDragging(false)
    onPick(event.dataTransfer.files[0] ?? null)
  }

  return (
    <div className="field">
      <label
        className={`drop${dragging ? ' dragging' : ''}${file ? ' has-file' : ''}`}
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <span className="field-label">CV (PDF, up to 5 MB)</span>
        <input
          id="cv"
          className="visually-hidden"
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => onPick(event.target.files?.[0] ?? null)}
        />
        <span className="drop-text">
          {file ? (
            <>
              <strong>{file.name}</strong> · {formatSize(file.size)} · click to change
            </>
          ) : (
            'Drop your PDF here, or click to choose one'
          )}
        </span>
      </label>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </div>
  )
}
