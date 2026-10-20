import sqlite3
from datetime import date

from fastapi import APIRouter, Depends

from backend import db
from backend.cards import to_card
from backend.deps import get_conn, owner_id
from backend.schemas import CardsCreate

router = APIRouter(prefix="/api/cards")


@router.get("")
def list_cards(
    owner: str = Depends(owner_id), conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    today = date.today()
    return {"items": [to_card(r, today) for r in db.list_remaining(conn, owner)]}


@router.post("", status_code=201)
def create_cards(
    body: CardsCreate,
    owner: str = Depends(owner_id),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    today = date.today()
    rows = db.insert_cards(conn, owner, [i.model_dump() for i in body.items])
    return {"items": [to_card(r, today) for r in rows]}
