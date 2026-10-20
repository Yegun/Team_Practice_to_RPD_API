import { strings } from '../strings'
import type { Draft } from '../types'

type Props = {
  drafts: Draft[]
  onBack: () => void
}

// 정리 결과 초안. 이름·수량·기한 수정과 저장은 US-03 에서 붙인다.
export function DraftReview({ drafts, onBack }: Props) {
  return (
    <section className="panel">
      <h2>{strings.draftTitle}</h2>
      <p>{strings.draftNotSaved}</p>
      <ul className="card-list">
        {drafts.map((d, i) => (
          <li key={i} className="card">
            <div className="card-main">
              <span className="card-name">{d.name}</span>
              <span className="card-qty">× {d.quantity}</span>
            </div>
            <div className="card-due">
              <span className="card-date">{d.due_date ?? strings.noDueDate}</span>
            </div>
          </li>
        ))}
      </ul>
      <div className="actions">
        <button type="button" onClick={onBack}>
          {strings.back}
        </button>
      </div>
    </section>
  )
}
