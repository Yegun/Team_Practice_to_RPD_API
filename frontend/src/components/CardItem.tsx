import { daysLabel } from '../format'
import { strings } from '../strings'
import type { Card } from '../types'

// 색에만 의존하지 않도록 남은 일수 글자를 항상 함께 보여 준다 (D-013).
export function CardItem({ card }: { card: Card }) {
  return (
    <li className={`card card-${card.urgency}`}>
      <div className="card-main">
        <span className="card-name">{card.name}</span>
        <span className="card-qty">× {card.quantity}</span>
      </div>
      <div className="card-tags">
        <span className={`tag tag-${card.storage}`}>{strings.storage[card.storage]}</span>
      </div>
      <div className="card-due">
        <span className={`badge badge-${card.urgency}`}>{daysLabel(card.days_left)}</span>
        {card.due_date && <span className="card-date">{card.due_date}</span>}
        {card.urgency === 'expired' && <span className="card-flag">{strings.expired}</span>}
        {card.urgency === 'urgent' && <span className="card-flag">{strings.urgent}</span>}
      </div>
    </li>
  )
}
