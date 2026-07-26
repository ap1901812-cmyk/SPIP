from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.sap.interface import SAPAdapterInterface


class RealSAPAdapter(SAPAdapterInterface):
    """Real SAP adapter placeholder/stub.
    Real SAP connectivity is a deferred external dependency that will be implemented
    behind the SAPAdapterInterface contract without altering core planning logic.
    """

    def fetch_plants(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def fetch_materials(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def fetch_vendors(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def fetch_consumption(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def fetch_inventory(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def fetch_purchase_orders(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def sync_to_database(self, db: Session) -> dict[str, int]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")

    def write_back_allocation(self, db: Session, allocation: Any) -> dict[str, Any]:
        raise NotImplementedError("Real SAP transport is a deferred external dependency.")
