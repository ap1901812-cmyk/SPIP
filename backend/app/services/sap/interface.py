from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session


class SAPAdapterInterface(ABC):
    """Authoritative abstract interface for SAP data integration.
    The SPIP application core depends exclusively on this interface contract.
    """

    @abstractmethod
    def fetch_plants() -> list[dict[str, Any]]:
        """Returns normalized list of plant records."""
        pass

    @abstractmethod
    def fetch_materials() -> list[dict[str, Any]]:
        """Returns normalized list of material records."""
        pass

    @abstractmethod
    def fetch_vendors() -> list[dict[str, Any]]:
        """Returns normalized list of vendor records."""
        pass

    @abstractmethod
    def fetch_consumption(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        """Returns normalized historical consumption observations (conceptually MB51)."""
        pass

    @abstractmethod
    def fetch_inventory(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        """Returns normalized stock/inventory snapshots (conceptually MB5B)."""
        pass

    @abstractmethod
    def fetch_purchase_orders(self, plant_code: str | None = None) -> list[dict[str, Any]]:
        """Returns normalized open purchase orders and lines (conceptually ME2N)."""
        pass

    @abstractmethod
    def sync_to_database(self, db: Session) -> dict[str, int]:
        """Ingests normalized SAP records into durable application database."""
        pass

    @abstractmethod
    def write_back_allocation(self, db: Session, allocation: Any) -> dict[str, Any]:
        """Executes controlled write-back of an approved allocation to SAP."""
        pass
