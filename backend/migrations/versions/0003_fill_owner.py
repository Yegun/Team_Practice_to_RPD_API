"""3단계 주인 채우기: 기존 카드를 모두 이전용 계정에 넘긴다 (D-023)

바뀌는 칸은 owner_id 뿐이다. 행은 지우지 않는다.
확인: 주인 없는 카드(owner_id 가 users 에 없는 카드)가 0 이다.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

MIGRATED_LOGIN_ID = "migrated@test.com"

_ORPHANS = "SELECT COUNT(*) FROM cards WHERE owner_id NOT IN (SELECT id FROM users)"


def upgrade() -> None:
    conn = op.get_bind()
    migrated_id = conn.execute(
        sa.text("SELECT id FROM users WHERE login_id = :l"), {"l": MIGRATED_LOGIN_ID}
    ).scalar()
    if migrated_id is None:
        raise RuntimeError("0003: 이전용 계정이 없다 (0002 가 먼저 적용되어야 한다)")

    before = conn.execute(sa.text("SELECT COUNT(*) FROM cards")).scalar()
    conn.execute(
        sa.text("UPDATE cards SET owner_id = :m WHERE owner_id <> :m"), {"m": migrated_id}
    )

    after = conn.execute(sa.text("SELECT COUNT(*) FROM cards")).scalar()
    orphans = conn.execute(sa.text(_ORPHANS)).scalar()
    if after != before or orphans != 0:
        raise RuntimeError(
            f"0003: 카드 수 {before} -> {after}, 주인 없는 카드 {orphans} (0 이어야 한다)"
        )


def downgrade() -> None:
    raise NotImplementedError(
        "원래 owner_id 를 복원할 수 없다. 이전 전에 만든 백업을 복원한다."
    )
