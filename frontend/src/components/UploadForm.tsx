import { useState } from 'react'
import { analyzeReceipt } from '../api'
import { strings } from '../strings'
import type { Draft } from '../types'
import { checkFile, uploadErrorMessage } from '../uploadRules'

type Props = {
  onDone: (items: Draft[]) => void
  onCancel: () => void
}

export function UploadForm({ onDone, onCancel }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const choose = (picked: File | null) => {
    setError(picked ? checkFile(picked) : null)
    setFile(picked)
  }

  const submit = async () => {
    if (!file || sending) return
    setSending(true)
    setError(null)
    try {
      const { items } = await analyzeReceipt(file)
      onDone(items)
    } catch (err) {
      setError(uploadErrorMessage(err))
      setSending(false)
    }
  }

  return (
    <section className="panel">
      <h2>{strings.uploadTitle}</h2>
      <p>{strings.uploadHelp}</p>

      <label className="file-label">
        <span>{strings.chooseFile}</span>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          disabled={sending}
          onChange={(e) => choose(e.target.files?.[0] ?? null)}
        />
      </label>
      {file && <p className="file-name">{file.name}</p>}

      {sending && <p role="status">{strings.analyzing}</p>}
      {error && (
        <p role="alert" className="notice notice-error">
          {error}
        </p>
      )}

      <div className="actions">
        <button type="button" onClick={onCancel} disabled={sending}>
          {strings.back}
        </button>
        <button
          type="button"
          className="primary"
          onClick={submit}
          disabled={!file || sending || checkFile(file) !== null}
        >
          {error && file && checkFile(file) === null ? strings.retry : strings.analyze}
        </button>
      </div>
    </section>
  )
}
