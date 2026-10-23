"""1단계 구조 추가: users, sessions 를 만든다 (cards 는 이미 있으면 그대로 둔다)

cards.owner_id 는 처음부터 NOT NULL 로 있으므로 칸을 새로 만들지 않고 테이블도 다시 만들지 않는다
(DATA-MIGRATION-PLAN 3절 (가)). 확인: cards 의 수와 내용이 그대로다.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _cards_fingerprint(conn) -> tuple[int, str]:
    has = conn.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='cards'")
    ).fetchone()
    if not has:
        return 0, ""
    rows = conn.execute(sa.text("SELECT * FROM cards ORDER BY id")).fetchall()
    return len(rows), repr([tuple(r) for r in rows])


def upgrade() -> None:
    conn = op.get_bind()
    before = _cards_fingerprint(conn)

    # 이미 앱이 만든 DB 에서도 돌아가도록 IF NOT EXISTS 를 쓴다.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id          TEXT PRIMARY KEY,
            owner_id    TEXT NOT NULL,
            name        TEXT NOT NULL,
            quantity    INTEGER NOT NULL,
            due_date    TEXT,
            storage     TEXT NOT NULL,
            is_risky    INTEGER NOT NULL,
            urgent_days INTEGER NOT NULL,
            status      TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_cards_owner_status ON cards (owner_id, status)"
    )
    # password_hash '' 는 "비밀번호 미설정" 이다. 로그인은 항상 실패한다 (MIGRATION 9절 8번).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            login_id      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at    TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires_at)")

    after = _cards_fingerprint(conn)
    if after != before:
        raise RuntimeError(f"0001: cards 수·내용이 바뀌었다 ({before[0]} -> {after[0]})")


def downgrade() -> None:
    raise NotImplementedError("되돌리지 않는다. 이전 전에 만든 백업을 복원한다.")
