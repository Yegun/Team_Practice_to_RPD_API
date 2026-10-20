import sqlite3
from datetime import date

from fastapi import APIRouter, Depends

from backend import db
from backend.cards import to_card
from backend.deps import get_conn, owner_id
from backend.errors import ApiError
from backend.schemas import CardPatch, CardsCreate

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


@router.patch("/{card_id}")
def update_card(
    card_id: str,
    body: CardPatch,
    owner: str = Depends(owner_id),
    conn: sqlite3.Connection = Depends(get_conn),
) -> dict:
    changes = {k: getattr(body, k) for k in body.model_fields_set}
    if not changes:
        raise ApiError(422, "VALIDATION_ERROR", "바꿀 필드가 없다.")
    if "status" in changes and len(changes) > 1:
        raise ApiError(
            422, "VALIDATION_ERROR", "수정 필드와 status 를 함께 보낼 수 없다.", ["status"]
        )
    row = db.get_card(conn, owner, card_id)
    if row is None:
        # 없는 카드와 남의 카드를 구분하지 않는다 (API-SPEC §1).
        raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없다.")

    if "status" in changes:
        target = changes["status"]
        if target == "archived" and row["status"] == "archived":
            raise ApiError(409, "CARD_ARCHIVED", "이미 정리된 카드다.")
        if target == "remaining" and row["status"] == "remaining":
            raise ApiError(409, "CARD_NOT_ARCHIVED", "이미 '남음' 상태인 카드다.")
        return to_card(db.set_status(conn, owner, card_id, target), date.today())

    if row["status"] == "archived":
        raise ApiError(409, "CARD_ARCHIVED", "이미 정리된 카드는 고칠 수 없다.")
    return to_card(db.update_card(conn, owner, card_id, changes), date.today())
