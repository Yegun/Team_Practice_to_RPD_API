import { useRef, useState } from 'react'
import { ApiRequestError, createCards } from '../api'
import { strings } from '../strings'
import type { Draft } from '../types'

type Props = {
  drafts: Draft[]
  onBack: () => void
  onSaved: () => void
}

// 입력 칸은 문자열로 들고 있다가 저장할 때 값으로 바꾼다.
type Row = { name: string; quantity: string; due_date: string }

function toBody(draft: Draft, row: Row): Draft {
  return {
    ...draft,
    name: row.name,
    // 빈 칸이나 숫자가 아닌 값은 그대로 보내 서버가 칸을 알려 주게 한다.
    quantity: row.quantity.trim() === '' ? (null as unknown as number) : Number(row.quantity),
    due_date: row.due_date === '' ? null : row.due_date,
  }
}

// 정리 결과 확인 (E-03). 저장하기 전에는 어떤 카드도 목록에 생기지 않는다 (D-006).
export function DraftReview({ drafts, onBack, onSaved }: Props) {
  const [rows, setRows] = useState<Row[]>(() =>
    drafts.map((d) => ({
      name: d.name,
      quantity: String(d.quantity),
      due_date: d.due_date ?? '',
    })),
  )
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [badFields, setBadFields] = useState<Set<string>>(new Set())
  const dateInputs = useRef<(HTMLInputElement | null)[]>([])

  const setRow = (i: number, patch: Partial<Row>) =>
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))

  const save = async () => {
    if (saving) return
    setMessage(null)
    setBadFields(new Set())
    // 날짜 칸은 날짜가 아닌 입력이면 값이 빈 문자열이 된다. 빈 칸(기한 없음)과 구분해서 보내지 않는다.
    const badDates = drafts.flatMap((_, i) =>
      dateInputs.current[i]?.validity.badInput ? [`items[${i}].due_date`] : [],
    )
    if (badDates.length > 0) {
      setBadFields(new Set(badDates))
      setMessage(strings.invalidInputs)
      return
    }
    setSaving(true)
    try {
      await createCards(drafts.map((d, i) => toBody(d, rows[i])))
      onSaved()
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === 'VALIDATION_ERROR') {
        setBadFields(new Set(err.fields))
        setMessage(strings.invalidInputs)
      } else {
        // 저장소 실패, 연결 끊김 등. 입력값은 그대로 둔다 (T-10).
        setMessage(strings.saveFailed)
      }
      setSaving(false)
    }
  }

  return (
    <section className="panel">
      <h2>{strings.draftTitle}</h2>
      <p>{strings.draftNotSaved}</p>
      <ul className="card-list">
        {rows.map((row, i) => (
          <li key={i} className="card">
            <Field
              label={strings.labelName}
              invalid={badFields.has(`items[${i}].name`)}
              message={strings.fieldErrors.name}
              input={
                <input
                  type="text"
                  value={row.name}
                  disabled={saving}
                  onChange={(e) => setRow(i, { name: e.target.value })}
                />
              }
            />
            <Field
              label={strings.labelQuantity}
              invalid={badFields.has(`items[${i}].quantity`)}
              message={strings.fieldErrors.quantity}
              input={
                <input
                  type="number"
                  inputMode="numeric"
                  step={1}
                  value={row.quantity}
                  disabled={saving}
                  onChange={(e) => setRow(i, { quantity: e.target.value })}
                />
              }
            />
            <Field
              label={strings.labelDueDate}
              invalid={badFields.has(`items[${i}].due_date`)}
              message={strings.fieldErrors.due_date}
              input={
                <input
                  ref={(el) => {
                    dateInputs.current[i] = el
                  }}
                  type="date"
                  value={row.due_date}
                  disabled={saving}
                  onChange={(e) => setRow(i, { due_date: e.target.value })}
                />
              }
            />
          </li>
        ))}
      </ul>

      {saving && <p role="status">{strings.saving}</p>}
      {message && (
        <p role="alert" className="notice notice-error">
          {message}
        </p>
      )}

      <div className="actions">
        <button type="button" onClick={onBack} disabled={saving}>
          {strings.back}
        </button>
        <button type="button" className="primary" onClick={save} disabled={saving}>
          {strings.save}
        </button>
      </div>
    </section>
  )
}

function Field({
  label,
  invalid,
  message = strings.fieldInvalid,
  input,
}: {
  label: string
  invalid: boolean
  message?: string
  input: React.ReactNode
}) {
  return (
    <label className={`field${invalid ? ' field-invalid' : ''}`}>
      <span>{label}</span>
      {input}
      {invalid && <span className="field-error">{message}</span>}
    </label>
  )
}
