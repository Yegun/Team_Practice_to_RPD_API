export type Storage = 'fridge' | 'freezer' | 'room'
export type Urgency = 'expired' | 'urgent' | 'ok' | 'unknown'

export type Draft = {
  name: string
  quantity: number
  due_date: string | null
  storage: Storage
  is_risky: boolean
  urgent_days: number
}

export type Card = Draft & {
  id: string
  status: 'remaining' | 'archived'
  created_at: string
  days_left: number | null
  urgency: Urgency
}
