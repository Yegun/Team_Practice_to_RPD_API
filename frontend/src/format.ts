import { strings } from './strings'

export function daysLabel(daysLeft: number | null): string {
  if (daysLeft === null) return strings.noDueDate
  if (daysLeft === 0) return strings.dueToday
  if (daysLeft > 0) return `D-${daysLeft}`
  return `D+${-daysLeft}`
}
