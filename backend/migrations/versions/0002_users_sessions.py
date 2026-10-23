"""2단계 이전용 계정: migrated@test.com 을 비밀번호 없이 만든다 (D-023)

확인: users 에 사용자가 한 명이다.

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
    row = conn.execute(
        sa.text("SELECT id FROM users WHERE login_id = :l"), {"l": MIGRATED_LOGIN_ID}
    ).fetchone()
    if row is None:
        conn.execute(
            sa.text(
                "INSERT INTO users (id, login_id, password_hash, created_at) "
                "VALUES (:i, :l, '', :t)"
            ),
            {
                "i": str(uuid.uuid4()),
                "l": MIGRATED_LOGIN_ID,
                "t": datetime.now(UTC).isoformat(),
            },
        )

    count = conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    if count != 1:
        raise RuntimeError(f"0002: 사용자가 한 명이어야 한다 (지금 {count})")


def downgrade() -> None:
    raise NotImplementedError("되돌리지 않는다. 이전 전에 만든 백업을 복원한다.")
