"""Shared pytest fixtures: every test gets its own SQLite file."""

from __future__ import annotations

import pytest

from core import db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("VE_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    yield
