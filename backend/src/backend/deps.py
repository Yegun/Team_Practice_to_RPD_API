from collections.abc import Iterator
import sqlite3

from fastapi import Cookie, Depends

from backend.auth import user_for_token
from backend.db import connect
from backend.errors import ApiError


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


def owner_id(user: sqlite3.Row = Depends(current_user)) -> str:
    """카드 소유자. 로그인한 사용자의 id 다. 요청 값으로 받지 않는다."""
    return user["id"]
