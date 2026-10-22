"""baseline: 로그인 도입 전의 cards 테이블

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    raise NotImplementedError("baseline 은 되돌리지 않는다. 백업을 복원한다.")
