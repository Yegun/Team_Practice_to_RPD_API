import sqlite3
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response

from backend import auth
from backend.deps import current_user, get_conn, session_token
from backend.errors import ApiError
from backend.schemas import LoginIn, SignupIn

router = APIRouter(prefix="/api/auth")


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        token,
        max_age=auth.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _user_body(user_id: str, login_id: str) -> dict:
    return {"user": {"id": user_id, "login_id": login_id}}


@router.post("/signup", status_code=201)
def signup(
    body: SignupIn, response: Response, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    password_hash = auth.hash_password(body.password)
    now = datetime.now(UTC).isoformat()
    try:
        with conn:
            existing = conn.execute(
                "SELECT id, password_hash FROM users WHERE login_id = ?", (body.login_id,)
            ).fetchone()
            if existing is None:
                user_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO users (id, login_id, password_hash, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (user_id, body.login_id, password_hash, now),
                )
            elif body.login_id == auth.MIGRATED_LOGIN_ID and existing["password_hash"] == "":
                # 이전용 계정은 처음 가입하는 사람이 비밀번호를 정해 받는다 (D-023).
                user_id = existing["id"]
                cur = conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ? AND password_hash = ''",
                    (password_hash, user_id),
                )
                if cur.rowcount != 1:
                    raise ApiError(409, "LOGIN_ID_TAKEN", "이미 쓰는 아이디다.", ["login_id"])
            else:
                raise ApiError(409, "LOGIN_ID_TAKEN", "이미 쓰는 아이디다.", ["login_id"])
    except sqlite3.IntegrityError:
        raise ApiError(409, "LOGIN_ID_TAKEN", "이미 쓰는 아이디다.", ["login_id"]) from None

    _set_cookie(response, auth.create_session(conn, user_id))
    return _user_body(user_id, body.login_id)


@router.post("/login")
def login(
    body: LoginIn, response: Response, conn: sqlite3.Connection = Depends(get_conn)
) -> dict:
    row = conn.execute(
        "SELECT id, login_id, password_hash FROM users WHERE login_id = ?", (body.login_id,)
    ).fetchone()
    # 아이디 없음, 비밀번호 틀림, 비밀번호 미설정을 구분하지 않는다.
    stored = row["password_hash"] if row else ""
    ok = auth.verify_password(body.password, stored)
    if row is None or not ok:
        raise ApiError(401, "INVALID_CREDENTIALS", "아이디나 비밀번호가 맞지 않다.")
    _set_cookie(response, auth.create_session(conn, row["id"]))
    return _user_body(row["id"], row["login_id"])


@router.post("/logout", status_code=204)
def logout(
    _user: sqlite3.Row = Depends(current_user),
    token: str | None = Depends(session_token),
    conn: sqlite3.Connection = Depends(get_conn),
) -> Response:
    assert token is not None
    auth.delete_session(conn, token)
    response = Response(status_code=204)
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return response


@router.get("/me")
def me(user: sqlite3.Row = Depends(current_user)) -> dict:
    return _user_body(user["id"], user["login_id"])
