"""users, sessions 추가, 기존 카드를 이전용 계정에 귀속 (D-023)

Revision ID: 0002
Revises: 0001
"""
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

MIGRATED_LOGIN_ID = "migrated@test.com"


def upgrade() -> None:
    conn = op.get_bind()
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

    row = conn.execute(
        sa.text("SELECT id FROM users WHERE login_id = :l"), {"l": MIGRATED_LOGIN_ID}
    ).fetchone()
    if row is None:
        migrated_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO users (id, login_id, password_hash, created_at) "
                "VALUES (:i, :l, '', :t)"
            ),
            {"i": migrated_id, "l": MIGRATED_LOGIN_ID, "t": datetime.now(UTC).isoformat()},
        )
    else:
        migrated_id = row[0]

    # 바뀌는 칸은 owner_id 뿐이다. 행은 지우지 않는다.
    conn.execute(
        sa.text("UPDATE cards SET owner_id = :m WHERE owner_id <> :m"), {"m": migrated_id}
    )


def downgrade() -> None:
    raise NotImplementedError(
        "원래 owner_id 를 복원할 수 없다. 이전 전에 만든 백업을 복원한다."
    )
