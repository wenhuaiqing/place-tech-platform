"""Shared fixtures.

The suite runs against the built database (scripts/build_platform.py). Tests
that write work on a throwaway copy, never the built one. No test calls a
model: the key is cleared, so the deterministic paths are what is tested,
and the agent is graded separately by evals/run_triage_eval.py.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="place-tests-"))
os.environ["DUCKDB_PATH"] = str(_TMP / "platform.duckdb")
os.environ["DEMO_WRITE_TOKEN"] = "test-token"
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_API_KEY"] = ""

from src.settings import settings  # noqa: E402

WRITE = {"X-Write-Token": "test-token"}


def as_(actor: str) -> dict[str, str]:
    return {**WRITE, "X-Actor": actor}


def pytest_collection_modifyitems(config, items):
    if not settings.build_db_path.exists():
        skip = pytest.mark.skip(reason="build first: uv run python ../scripts/build_platform.py")
        for item in items:
            item.add_marker(skip)


@pytest.fixture()
def fresh_db():
    from src.app.services import db
    db.reset_to_build()
    yield db
    db.reset_to_build()


@pytest.fixture()
def client(fresh_db):
    from fastapi.testclient import TestClient

    from src.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def built():
    import duckdb
    con = duckdb.connect(str(settings.build_db_path), read_only=True)
    yield con
    con.close()


def tool_id(con, key: str) -> str:
    """The register's id for a tool the reference declares, found the way a
    person would: by its repository, agent id or hosting resource."""
    from src.app.pipeline import reference as ref
    t = next(t for t in ref.TOOLS if t["key"] == key)
    row = con.execute("""SELECT tool_id FROM tool WHERE repo = ? OR agent_id = ? OR site = ? OR repo_candidates LIKE ?""",
                      [t.get("repo"), t.get("agent_id"), t.get("site") or t.get("project"), f"%{t.get('repo')}%"]).fetchone()
    return row[0]


def pytest_sessionfinish(session, exitstatus):
    from src.app.services import db
    try:
        if db._con is not None:
            db._con.close()
    except Exception:  # noqa: BLE001
        pass
    shutil.rmtree(_TMP, ignore_errors=True)
