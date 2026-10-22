import importlib.util
import sqlite3
import uuid
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_with_backup.py"
_spec = importlib.util.spec_from_file_location("migrate_with_backup", _SCRIPT)
mwb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mwb)

OLD_SCHEMA = """
CREATE TABLE cards (
    id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL,
    quantity INTEGER NOT NULL, due_date TEXT, storage TEXT NOT NULL,
    is_risky INTEGER NOT NULL, urgent_days INTEGER NOT NULL, status TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX idx_cards_owner_status ON cards (owner_id, status);
"""


@pytest.fixture
def old_db(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(mwb, "BACKUP_DIR", tmp_path / "backups")
    path = tmp_path / "foods.db"
    conn = sqlite3.connect(path)
    conn.executescript(OLD_SCHEMA)
    for i in range(5):
        conn.execute(
            "INSERT INTO cards VALUES (?, ?, ?, 1, ?, 'fridge', 0, 3, ?, 't', 't')",
            (
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                f"식품{i}",
                None if i == 0 else "2026-11-01",
                "archived" if i == 4 else "remaining",
            ),
        )
    conn.commit()
    conn.close()
    return path


def test_migration_moves_all_cards_to_migrated_user(old_db):
    before = mwb.snapshot(old_db)
    assert mwb.main(["x", str(old_db)]) == 0
    after = mwb.snapshot(old_db)
    assert after["total"] == before["total"] == 5
    assert after["by_status"] == before["by_status"]
    assert len(after["by_owner"]) == 1
    conn = sqlite3.connect(old_db)
    users = conn.execute("SELECT login_id, password_hash FROM users").fetchall()
    assert users == [("migrated@test.com", "")]
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    conn.close()


def test_backup_is_kept_and_unchanged(old_db, tmp_path):
    before = mwb.snapshot(old_db)
    mwb.main(["x", str(old_db)])
    baks = list((tmp_path / "backups").glob("*.bak"))
    assert len(baks) == 1
    assert mwb.snapshot(baks[0]) == before


def test_mismatch_restores_backup(old_db, monkeypatch, tmp_path):
    before = mwb.snapshot(old_db)
    real_upgrade = mwb.upgrade

    def lossy(path):
        real_upgrade(path)
        if path == old_db:  # 본 DB 적용 뒤 카드 한 건이 사라지는 상황
            c = sqlite3.connect(path)
            c.execute("DELETE FROM cards WHERE rowid = 1")
            c.commit()
            c.close()

    monkeypatch.setattr(mwb, "upgrade", lossy)
    assert mwb.main(["x", str(old_db)]) == 3
    assert mwb.snapshot(old_db) == before
    conn = sqlite3.connect(old_db)
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name='users'").fetchone() is None
    conn.close()
    assert list(tmp_path.glob("foods.db.broken-*"))


def test_upgrade_is_safe_on_db_created_by_app(tmp_path, monkeypatch):
    # 앱이 이미 users, sessions 를 만든 DB 에서도 적용된다.
    from backend.db import connect

    path = tmp_path / "app.db"
    monkeypatch.setenv("FOODS_DB_PATH", str(path))
    connect().close()
    mwb.upgrade(path)
    conn = sqlite3.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    conn.close()
