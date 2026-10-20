import sqlite3
from datetime import date


def days_left(due_date: str | None, today: date) -> int | None:
    if due_date is None:
        return None
    return (date.fromisoformat(due_date) - today).days


def urgency(left: int | None, urgent_days: int) -> str:
    if left is None:
        return "unknown"
    if left < 0:
        return "expired"
    if left <= urgent_days:
        return "urgent"
    return "ok"


def to_card(row: sqlite3.Row, today: date) -> dict:
    left = days_left(row["due_date"], today)
    return {
        "id": row["id"],
        "name": row["name"],
        "quantity": row["quantity"],
        "due_date": row["due_date"],
        "storage": row["storage"],
        "is_risky": bool(row["is_risky"]),
        "urgent_days": row["urgent_days"],
        "status": row["status"],
        "created_at": row["created_at"],
        "days_left": left,
        "urgency": urgency(left, row["urgent_days"]),
    }
