from decimal import Decimal

import pytest

from app.domain import ServiceRecord
from app.services.offers import ValidationError, calculate_preview
from app.repositories.pvudb import PVUDBRepository


def record(charge="100.00"):
    return ServiceRecord("P1", "Plan", "3504", "Campaña", "Solución", "T", "SP", "SN1", "S1", "Internet", Decimal("84.75"), Decimal(charge), "Servicio", "P1-3504-SN1")


def test_fixed_discount_preview():
    preview = calculate_preview([record()], ["P1-3504-SN1"], "fixed", "10", 12, {})
    assert preview["counts"]["new"] == 1
    assert preview["operations"][0]["new_charge"] == "90.00"


def test_percentage_discount_preview():
    preview = calculate_preview([record()], ["P1-3504-SN1"], "percent", "15", 6, {})
    assert preview["operations"][0]["discount_value"] == "15.00"
    assert preview["operations"][0]["new_charge"] == "85.00"


@pytest.mark.parametrize("discount_type,value,period", [("fixed", "-1", 12), ("percent", "101", 12), ("fixed", "10", 7)])
def test_invalid_discount_is_rejected(discount_type, value, period):
    with pytest.raises(ValidationError):
        calculate_preview([record()], ["P1-3504-SN1"], discount_type, value, period, {})


def test_duplicate_selection_is_rejected():
    with pytest.raises(ValidationError):
        calculate_preview([record()], ["P1-3504-SN1", "P1-3504-SN1"], "fixed", "10", 12, {})


def test_existing_identical_record_is_unchanged():
    existing = {"P1-3504-SN1": {"dscto": "10.00", "periodo": 12}}
    preview = calculate_preview([record()], ["P1-3504-SN1"], "fixed", "10", 12, existing)
    assert preview["counts"]["unchanged"] == 1


def test_authorized_sql_keeps_union_and_bound_parameter():
    repository = PVUDBRepository(None, "sql/pvudb_campaign.sql")
    sql = repository._load_sql()
    assert "UNION ALL" in sql.upper()
    assert ":codigo_campana" in sql
    assert "CAMPANA IN (3504,3216,3454" not in sql


def test_batch_limit_is_enforced():
    with pytest.raises(ValidationError):
        calculate_preview([record()], [f"key-{n}" for n in range(501)], "fixed", "10", 12, {})

