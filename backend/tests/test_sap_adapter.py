from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.sap import MockSAPAdapter, RealSAPAdapter, get_sap_adapter


def test_mock_sap_adapter_deterministic_data() -> None:
    adapter = MockSAPAdapter()
    plants = adapter.fetch_plants()
    materials = adapter.fetch_materials()
    vendors = adapter.fetch_vendors()
    consumption = adapter.fetch_consumption()
    inventory = adapter.fetch_inventory()
    pos = adapter.fetch_purchase_orders()

    assert len(plants) == 2
    assert len(materials) >= 5
    assert len(vendors) == 3
    assert len(consumption) > 0
    assert len(inventory) > 0
    assert len(pos) > 0


def test_mock_sap_adapter_sync_to_database(db_session: Session) -> None:
    adapter = MockSAPAdapter()
    counts = adapter.sync_to_database(db_session)

    assert counts["plants"] == 2
    assert counts["materials"] >= 5
    assert counts["vendors"] == 3
    assert counts["consumption"] > 0
    assert counts["inventory"] > 0
    assert counts["purchase_orders"] > 0


def test_sap_adapter_factory_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("SAP_ADAPTER_MODE", "mock")
    mock_adapter = get_sap_adapter()
    assert isinstance(mock_adapter, MockSAPAdapter)

    get_settings.cache_clear()
    monkeypatch.setenv("SAP_ADAPTER_MODE", "real")
    real_adapter = get_sap_adapter()
    assert isinstance(real_adapter, RealSAPAdapter)

    with pytest.raises(NotImplementedError):
        real_adapter.fetch_plants()

    get_settings.cache_clear()


def test_mock_sap_adapter_plant_filtering() -> None:
    adapter = MockSAPAdapter()
    plant_1000_inventory = adapter.fetch_inventory(plant_code="PLANT-1000")
    assert all(item["plant_code"] == "PLANT-1000" for item in plant_1000_inventory)
