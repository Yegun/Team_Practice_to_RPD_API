"""비밀번호 해시와 세션. 표준 라이브러리만 쓴다 (API-SPEC-CHANGE §2, §8)."""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# backend/.env 의 값을 읽는다. 이미 있는 환경변수는 덮어쓰지 않는다.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

COOKIE_NAME = "session"
SESSION_MAX_AGE = 30 * 60  # D-024
MIGRATED_LOGIN_ID = "migrated@test.com"  # D-023

_N, _R, _P = 2**14, 8, 1


def session_secret() -> bytes:
    value = os.environ.get("SESSION_SECRET", "")
    if not value:
        raise RuntimeError("SESSION_SECRET 이 없다. backend/.env 에 값을 넣는다.")
    return value.encode()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


# 아이디가 없을 때도 같은 시간을 쓰기 위한 값
_DUMMY_HASH = hash_password("dummy-password")


def verify_password(password: str, stored: str) -> bool:
    """stored 가 빈 문자열이면 비밀번호 미설정(이전용 계정)이라 항상 False 다."""
    if not stored:
        stored = _DUMMY_HASH
        valid = False
    else:
        valid = True
    try:
        _, n, r, p, salt, digest = stored.split("$")
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, bytes.fromhex(digest)) and valid


def _now() -> datetime:
    return datetime.now(UTC)


def _session_id(token: str) -> str:
    return hmac.new(session_secret(), token.encode(), hashlib.sha256).hexdigest()


def create_session(conn: sqlite3.Connection, user_id: str) -> str:
    """세션을 만들고 쿠키에 실을 원본 값을 돌려준다. DB 에는 해시만 둔다."""
    now = _now()
    token = secrets.token_urlsafe(32)
    with conn:
        # 만료된 세션은 로그인할 때 지운다.
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now.isoformat(),))
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (
                _session_id(token),
                user_id,
                now.isoformat(),
                (now + timedelta(seconds=SESSION_MAX_AGE)).isoformat(),
            ),
        )
    return token


def user_for_token(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        "SELECT u.id, u.login_id FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.id = ? AND s.expires_at > ?",
        (_session_id(token), _now().isoformat()),
    ).fetchone()


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    with conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (_session_id(token),))
