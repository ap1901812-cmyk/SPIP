from __future__ import annotations

import importlib.util

import pytest
from sqlalchemy import create_engine, inspect


def test_migration_008_structure() -> None:
    # Dynamically import the alembic migration script
    from pathlib import Path
    migration_path = Path(__file__).parent.parent / "alembic" / "versions" / "008_spip_v2_schema.py"
    spec = importlib.util.spec_from_file_location(
        "migration_008",
        str(migration_path),
    )
    assert spec is not None and spec.loader is not None
    migration_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_mod)

    assert migration_mod.revision == "008_spip_v2_schema"
    assert migration_mod.down_revision == "007_user_management"
    assert callable(migration_mod.upgrade)
    assert callable(migration_mod.downgrade)
