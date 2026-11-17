import pytest

from app import create_app
from app.repositories.dwo import DWORepository


def test_production_requires_secret(tmp_path):
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        create_app({
            "TESTING": True,
            "APP_ENV": "production",
            "SECRET_KEY": "development-only-change-me",
            "DATABASE_PATH": str(tmp_path / "test.db"),
            "AUDIT_LOG_PATH": str(tmp_path / "audit.log"),
        })


def test_dwo_write_gate_stays_closed():
    repository = DWORepository(None, {
        "DWO_WRITE_ENABLED": True,
        "DWO_MAPPING_VERIFIED": False,
        "DWO_BUSINESS_RULES_VERIFIED": True,
        "DWO_KEY_VERIFIED": True,
    })
    with pytest.raises(PermissionError, match="cerrada"):
        repository._assert_write_gate()
