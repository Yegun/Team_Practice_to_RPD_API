"""4단계 필수로: owner_id 를 비울 수 없게 확인한다

cards.owner_id 는 처음부터 NOT NULL 이라 테이블을 새로 만들지 않는다 (DATA-MIGRATION-PLAN 3절 (가)).
칸이 NOT NULL 인지, 비었거나 users 에 없는 주인이 없는지 확인하고 아니면 멈춘다.
확인: cards 의 수와 내용이 그대로다.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT * FROM cards ORDER BY id")).fetchall()
    before = (len(rows), repr([tuple(r) for r in rows]))

    owner_col = [
        c for c in conn.execute(sa.text("PRAGMA table_info(cards)")).fetchall() if c[1] == "owner_id"
    ]
    if not owner_col or owner_col[0][3] != 1:
        raise RuntimeError("0004: cards.owner_id 가 NOT NULL 이 아니다")

    bad = conn.execute(
        sa.text(
            "SELECT COUNT(*) FROM cards "
            "WHERE owner_id IS NULL OR owner_id = '' OR owner_id NOT IN (SELECT id FROM users)"
        )
    ).scalar()
    if bad:
        raise RuntimeError(f"0004: 주인이 없거나 users 에 없는 카드가 {bad} 건 있다")

    rows = conn.execute(sa.text("SELECT * FROM cards ORDER BY id")).fetchall()
    if (len(rows), repr([tuple(r) for r in rows])) != before:
        raise RuntimeError("0004: cards 수·내용이 바뀌었다")


def downgrade() -> None:
    raise NotImplementedError("되돌리지 않는다. 이전 전에 만든 백업을 복원한다.")
