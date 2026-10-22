"""alembic upgrade 를 백업과 수량 비교로 감싼다 (DATA-MIGRATION-PLAN 5, 6절).

순서: 백업 -> 수량 기록 -> 작업용 복사본에 적용해 비교 -> 본 DB 적용 -> 비교.
수량이 다르면 멈추고 백업을 복원한다. 쓰는 법:

    uv run python scripts/migrate_with_backup.py [DB 경로]

DB 경로를 생략하면 FOODS_DB_PATH 를 쓴다. 서버는 멈춘 상태여야 한다.
"""
import hashlib
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]
BACKUP_DIR = BACKEND / "backups"
MIGRATED = "migrated@test.com"


def snapshot(path: Path) -> dict:
    """cards 의 수량 기록. 백업과 이전 결과를 비교하는 데 쓴다."""
    conn = sqlite3.connect(path)
    try:
        has_cards = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cards'"
        ).fetchone()
        if not has_cards:
            return {"total": 0, "by_status": [], "ids": "", "null_due": 0, "by_owner": []}
        ids = [r[0] for r in conn.execute("SELECT id FROM cards ORDER BY id")]
        return {
            "total": conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0],
            "by_status": [
                tuple(r)
                for r in conn.execute(
                    "SELECT status, COUNT(*) FROM cards GROUP BY status ORDER BY status"
                )
            ],
            "ids": hashlib.sha256("\n".join(ids).encode()).hexdigest(),
            "null_due": conn.execute(
                "SELECT COUNT(*) FROM cards WHERE due_date IS NULL"
            ).fetchone()[0],
            "by_owner": [
                tuple(r)
                for r in conn.execute(
                    "SELECT owner_id, COUNT(*) FROM cards GROUP BY owner_id ORDER BY owner_id"
                )
            ],
        }
    finally:
        conn.close()


def other_columns(path: Path) -> str:
    """owner_id 를 뺀 모든 칸의 해시. owner_id 외의 칸이 바뀌지 않았는지 본다."""
    conn = sqlite3.connect(path)
    try:
        has_cards = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cards'"
        ).fetchone()
        if not has_cards:
            return ""
        rows = conn.execute(
            "SELECT id, name, quantity, due_date, storage, is_risky, urgent_days, "
            "status, created_at, updated_at FROM cards ORDER BY id"
        ).fetchall()
        return hashlib.sha256(repr([tuple(r) for r in rows]).encode()).hexdigest()
    finally:
        conn.close()


def check_after(path: Path, before: dict, before_cols: str) -> list[str]:
    """6절 비교. 어긋난 항목을 문장으로 돌려준다. 비어 있으면 통과."""
    after = snapshot(path)
    problems = []
    for key in ("total", "by_status", "ids", "null_due"):
        if after[key] != before[key]:
            problems.append(f"{key}: {before[key]!r} -> {after[key]!r}")
    if other_columns(path) != before_cols:
        problems.append("owner_id 외의 칸이 바뀌었다")
    conn = sqlite3.connect(path)
    try:
        mid = conn.execute(
            "SELECT id FROM users WHERE login_id = ?", (MIGRATED,)
        ).fetchone()
        if mid is None:
            problems.append("이전용 계정이 없다")
        else:
            other = conn.execute(
                "SELECT COUNT(*) FROM cards WHERE owner_id <> ?", (mid[0],)
            ).fetchone()[0]
            if other:
                problems.append(f"이전용 계정이 아닌 카드가 {other} 건 있다")
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 1:
            problems.append("users 가 1 건이 아니다")
        if conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] != 0:
            problems.append("sessions 가 비어 있지 않다")
    finally:
        conn.close()
    return problems


def backup(src: Path, dst: Path) -> None:
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()


def upgrade(path: Path) -> None:
    os.environ["FOODS_DB_PATH"] = str(path)
    cfg = Config(str(BACKEND / "alembic.ini"))
    command.upgrade(cfg, "head")


def main(argv: list[str]) -> int:
    target = (
        Path(argv[1])
        if len(argv) > 1
        else Path(os.environ.get("FOODS_DB_PATH", BACKEND / "foods.db"))
    )
    if not target.exists():
        print(f"DB 파일이 없다: {target}. 이전할 것이 없다.")
        return 1

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = BACKUP_DIR / f"{target.stem}-{stamp}.bak"
    backup(target, bak)
    before = snapshot(bak)
    before_cols = other_columns(bak)
    print(f"백업: {bak}")
    print(
        f"적용 전 수량: total={before['total']} status={before['by_status']} "
        f"null_due={before['null_due']} owners={before['by_owner']}"
    )

    # 5-2: 작업용 복사본에서 먼저 확인한다. 본 DB 는 건드리지 않는다.
    work = BACKUP_DIR / f"{target.stem}-{stamp}.work"
    shutil.copyfile(bak, work)
    try:
        upgrade(work)
        problems = check_after(work, before, before_cols)
    finally:
        work.unlink(missing_ok=True)
    if problems:
        print("복사본 확인 실패. 본 DB 는 바뀌지 않았다:", *problems, sep="\n  ")
        return 2

    # 5-4: 본 DB 적용. 어긋나면 백업을 복원한다.
    try:
        upgrade(target)
        problems = check_after(target, before, before_cols)
    except Exception as exc:  # noqa: BLE001
        problems = [f"적용 중 오류: {exc!r}"]
    if problems:
        print("수량 불일치. 백업을 복원한다:", *problems, sep="\n  ")
        broken = target.with_name(f"{target.name}.broken-{stamp}")
        shutil.move(target, broken)
        shutil.copyfile(bak, target)
        restored = snapshot(target)
        print(f"복원 완료. 깨진 파일은 {broken} 에 둔다. 복원 후 total={restored['total']}")
        return 3

    print("완료. 수량이 모두 같다. 백업은 일주일 정도 지우지 않는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
