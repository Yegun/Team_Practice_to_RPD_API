import { strings } from '../strings'
import type { Card } from '../types'
import { CardItem } from './CardItem'

export type ListState =
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'ready'; items: Card[] }

type Props = {
  state: ListState
  busy: boolean
  onRetry: () => void
  onEdit: (card: Card) => void
  onArchive: (card: Card) => void
}

// 불러오는 중(T-02), 빈 목록(T-04), 불러오기 실패(T-05)는 서로 다른 화면이다.
export function CardList({ state, busy, onRetry, onEdit, onArchive }: Props) {
  if (state.kind === 'loading') {
    return <p role="status">{strings.loading}</p>
  }
  if (state.kind === 'error') {
    return (
      <div role="alert" className="notice notice-error">
        <p>{strings.loadFailed}</p>
        <button type="button" onClick={onRetry}>
          {strings.retry}
        </button>
      </div>
    )
  }
  if (state.items.length === 0) {
    return <p className="notice">{strings.emptyList}</p>
  }
  return (
    <ul className="card-list">
      {state.items.map((card) => (
        <CardItem key={card.id} card={card} busy={busy} onEdit={onEdit} onArchive={onArchive} />
      ))}
    </ul>
  )
}
