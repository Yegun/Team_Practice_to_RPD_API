import uuid
from collections.abc import Iterator
import sqlite3

from fastapi import Header

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
