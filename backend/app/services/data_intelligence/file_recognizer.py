from __future__ import annotations

import enum


class DatasetTypeEnum(enum.StrEnum):
    CONSUMPTION = "consumption"
    INVENTORY = "inventory"
    PURCHASE_ORDERS = "purchase_orders"
    MATERIAL_MASTER = "material_master"
    VENDOR_MASTER = "vendor_master"
    PLANT_MASTER = "plant_master"
    GRN = "grn"
    IBP_PLANNING = "ibp_planning"
    MONTHLY_REQUIREMENT = "monthly_requirement"
    VENDOR_CAPACITY = "vendor_capacity"
    VEHICLE_CAPACITY = "vehicle_capacity"
    MATERIAL_PARAMETERS = "material_parameters"
    UNKNOWN = "unknown"


# Signatures matching normalized headers (lowercase, stripped, underscores)
DATASET_SIGNATURES: dict[DatasetTypeEnum, set[str]] = {
    DatasetTypeEnum.CONSUMPTION: {"plant_code", "material_code", "quantity"},
    DatasetTypeEnum.INVENTORY: {"plant_code", "material_code", "usable_stock"},
    DatasetTypeEnum.PURCHASE_ORDERS: {"po_number", "vendor_code", "order_quantity"},
    DatasetTypeEnum.MATERIAL_MASTER: {"code", "description"},
    DatasetTypeEnum.VENDOR_MASTER: {"code", "name"},
    DatasetTypeEnum.PLANT_MASTER: {"code", "location"},
    DatasetTypeEnum.GRN: {"grn_number", "po_number", "received_quantity"},
    DatasetTypeEnum.IBP_PLANNING: {"planning_date", "ibp_daily_requirement"},
    DatasetTypeEnum.MONTHLY_REQUIREMENT: {"monthly_requirement"},
    DatasetTypeEnum.VENDOR_CAPACITY: {"vendor_code", "capacity_per_day"},
    DatasetTypeEnum.VEHICLE_CAPACITY: {"vehicle_type", "vehicle_capacity"},
    DatasetTypeEnum.MATERIAL_PARAMETERS: {"lead_time_1", "safety_stock_1"},
}

ALT_SIGNATURES: dict[DatasetTypeEnum, list[set[str]]] = {
    DatasetTypeEnum.CONSUMPTION: [
        {"plant", "material", "quantity_consumed"},
        {"posting_date", "quantity_consumed"},
    ],
    DatasetTypeEnum.INVENTORY: [
        {"usable_physical_stock"},
        {"stock_quantity"},
    ],
    DatasetTypeEnum.PURCHASE_ORDERS: [
        {"po_id", "open_quantity"},
        {"purchase_order", "vendor"},
    ],
    DatasetTypeEnum.MATERIAL_MASTER: [
        {"material_code", "material_description"},
    ],
    DatasetTypeEnum.VENDOR_MASTER: [
        {"vendor_code", "vendor_name"},
    ],
    DatasetTypeEnum.PLANT_MASTER: [
        {"plant_code", "plant_name"},
    ],
    DatasetTypeEnum.GRN: [
        {"gate_entry", "po_number"},
    ],
    DatasetTypeEnum.IBP_PLANNING: [
        {"ibp_requirement"},
        {"daily_requirement"},
    ],
    DatasetTypeEnum.MONTHLY_REQUIREMENT: [
        {"monthly_demand"},
        {"monthly_req"},
    ],
    DatasetTypeEnum.VENDOR_CAPACITY: [
        {"vendor_lead_time_days"},
    ],
    DatasetTypeEnum.VEHICLE_CAPACITY: [
        {"carrier_code", "capacity_kg"},
    ],
    DatasetTypeEnum.MATERIAL_PARAMETERS: [
        {"lead_time_days", "safety_stock"},
        {"trigger_1", "trigger_2"},
    ],
}


def recognize_file_type(headers: list[str] | set[str]) -> DatasetTypeEnum:
    """Automatically determine dataset type based on column signatures."""
    norm_headers = {h.strip().lower().replace(" ", "_") for h in headers if h}

    # 1. Direct signature subset check
    best_match: DatasetTypeEnum = DatasetTypeEnum.UNKNOWN
    max_matches = 0

    for dtype, sig in DATASET_SIGNATURES.items():
        if sig.issubset(norm_headers):
            return dtype
        match_count = len(sig.intersection(norm_headers))
        if match_count > max_matches and match_count >= 2:
            max_matches = match_count
            best_match = dtype

    # 2. Check alternative signatures
    for dtype, alt_list in ALT_SIGNATURES.items():
        for sig in alt_list:
            if sig.issubset(norm_headers):
                return dtype

    return best_match
