import { useState } from 'react'
import { ApiRequestError, updateCard, type CardPatch } from '../api'
import { strings } from '../strings'
import type { Card, Storage } from '../types'

type Props = {
  card: Card
  onCancel: () => void
  // 수정이 끝났거나, 카드를 찾을 수 없어 목록을 새로 읽어야 할 때 부른다. 안내가 있으면 같이 넘긴다.
  onDone: (notice?: string) => void
}

const STORAGES: Storage[] = ['fridge', 'freezer', 'room']

// 저장된 카드 수정 (E-06). 이름, 수량, 기한, 보관 방법, 위험 여부를 고칠 수 있다 (D-012).
export function CardEditForm({ card, onCancel, onDone }: Props) {
  const [name, setName] = useState(card.name)
  const [quantity, setQuantity] = useState(String(card.quantity))
  const [dueDate, setDueDate] = useState(card.due_date ?? '')
  const [storage, setStorage] = useState<Storage>(card.storage)
  const [isRisky, setIsRisky] = useState(card.is_risky)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [badFields, setBadFields] = useState<Set<string>>(new Set())

  const save = async () => {
    if (saving) return
    // 바뀐 값만 보낸다.
    const patch: CardPatch = {}
    if (name !== card.name) patch.name = name
    if (quantity !== String(card.quantity)) {
      patch.quantity = quantity.trim() === '' ? (null as unknown as number) : Number(quantity)
    }
    if (dueDate !== (card.due_date ?? '')) patch.due_date = dueDate === '' ? null : dueDate
    if (storage !== card.storage) patch.storage = storage
    if (isRisky !== card.is_risky) patch.is_risky = isRisky

    if (Object.keys(patch).length === 0) {
      onCancel()
      return
    }

    setSaving(true)
    setMessage(null)
    setBadFields(new Set())
    try {
      await updateCard(card.id, patch)
      onDone()
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === 'VALIDATION_ERROR') {
        setBadFields(new Set(err.fields))
        setMessage(strings.invalidInputs)
      } else if (
        err instanceof ApiRequestError &&
        (err.code === 'CARD_NOT_FOUND' || err.code === 'CARD_ARCHIVED')
      ) {
        // 찾을 수 없음 · 이미 정리됨 (T-11). 목록을 새로 읽는다.
        onDone(strings.cardGone)
        return
      } else {
        setMessage(strings.saveFailed)
      }
      setSaving(false)
    }
  }

  const bad = (field: string) => badFields.has(field)

  return (
    <section className="panel">
      <h2>{strings.editTitle}</h2>

      <label className={`field${bad('name') ? ' field-invalid' : ''}`}>
        <span>{strings.labelName}</span>
        <input type="text" value={name} disabled={saving} onChange={(e) => setName(e.target.value)} />
        {bad('name') && <span className="field-error">{strings.fieldInvalid}</span>}
      </label>

      <label className={`field${bad('quantity') ? ' field-invalid' : ''}`}>
        <span>{strings.labelQuantity}</span>
        <input
          type="number"
          inputMode="numeric"
          step={1}
          value={quantity}
          disabled={saving}
          onChange={(e) => setQuantity(e.target.value)}
        />
        {bad('quantity') && <span className="field-error">{strings.fieldInvalid}</span>}
      </label>

      <label className={`field${bad('due_date') ? ' field-invalid' : ''}`}>
        <span>{strings.labelDueDate}</span>
        <input
          type="date"
          value={dueDate}
          disabled={saving}
          onChange={(e) => setDueDate(e.target.value)}
        />
        {bad('due_date') && <span className="field-error">{strings.fieldInvalid}</span>}
      </label>

      <label className="field">
        <span>{strings.labelStorage}</span>
        <select
          value={storage}
          disabled={saving}
          onChange={(e) => setStorage(e.target.value as Storage)}
        >
          {STORAGES.map((s) => (
            <option key={s} value={s}>
              {strings.storage[s]}
            </option>
          ))}
        </select>
      </label>

      <label className="field field-check">
        <input
          type="checkbox"
          checked={isRisky}
          disabled={saving}
          onChange={(e) => setIsRisky(e.target.checked)}
        />
        <span>{strings.labelRisky}</span>
      </label>

      {saving && <p role="status">{strings.saving}</p>}
      {message && (
        <p role="alert" className="notice notice-error">
          {message}
        </p>
      )}

      <div className="actions">
        <button type="button" onClick={onCancel} disabled={saving}>
          {strings.cancel}
        </button>
        <button type="button" className="primary" onClick={save} disabled={saving}>
          {strings.save}
        </button>
      </div>
    </section>
  )
}
