import uuid
from collections.abc import Iterator
import sqlite3

from fastapi import Cookie, Depends, Header

from backend.auth import user_for_token
from backend.db import connect
from backend.errors import ApiError


def owner_id(x_owner_id: str | None = Header(default=None)) -> str:
    try:
        return str(uuid.UUID(x_owner_id))
    except (ValueError, TypeError, AttributeError):
        raise ApiError(
            400, "OWNER_MISSING", "X-Owner-Id 헤더가 없거나 UUID 형식이 아니다."
        ) from None


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def session_token(session: str | None = Cookie(default=None)) -> str | None:
    return session


def current_user(
    token: str | None = Depends(session_token),
    conn: sqlite3.Connection = Depends(get_conn),
) -> sqlite3.Row:
    user = user_for_token(conn, token)
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요하다.")
    return user
