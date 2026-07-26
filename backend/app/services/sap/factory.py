from __future__ import annotations

from app.core.config import get_settings
from app.services.sap.interface import SAPAdapterInterface
from app.services.sap.mock import MockSAPAdapter
from app.services.sap.real import RealSAPAdapter


def get_sap_adapter() -> SAPAdapterInterface:
    """Returns configured SAP adapter instance based on application settings."""
    settings = get_settings()
    if settings.sap_adapter_mode == "real":
        return RealSAPAdapter()
    return MockSAPAdapter()
