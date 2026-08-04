from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.errors import AppError


class FormulaExplorerEntry(BaseModel):
    id: str
    formula_name: str
    source_module: str
    mathematical_formula: str | None = None
    business_description: str
    required_inputs: list[str] = Field(default_factory=list)
    generated_outputs: list[str] = Field(default_factory=list)
    last_updated_version: str = "SPIP V2.0"


class AdminFormulaExplorerRegistry:
    """Read-only registry exposing every business formula and planning rule in SPIP V2 for Admin inspection."""

    _entries: list[FormulaExplorerEntry] = [
        FormulaExplorerEntry(
            id="EDI-01",
            formula_name="Enterprise Data Intelligence - Quality Scanner Rules",
            source_module="Enterprise Data Intelligence",
            mathematical_formula="DataQualityScore = 100.0 - (MissingMasterCount * 10.0 + DuplicateCount * 5.0)",
            business_description="Analyzes uploaded master data files (SAP MB5B, MB51, PlantMaterial) to detect missing parameters or corrupted formats prior to planning execution.",
            required_inputs=["Material code", "Plant code", "Base UOM", "Consumption records"],
            generated_outputs=["Data quality scan summary", "Missing parameter alerts"],
        ),
        FormulaExplorerEntry(
            id="EDI-02",
            formula_name="Enterprise Data Intelligence - Auto Master Generation Rules",
            source_module="Enterprise Data Intelligence",
            mathematical_formula="Default_SS_1 = D_avg * 7.0, Default_LT_1 = 10.0",
            business_description="Automatically generates default PlantMaterial master parameter placeholders when new SAP material codes are ingested without existing parameters.",
            required_inputs=["Material code", "Plant code", "Material type"],
            generated_outputs=["Generated PlantMaterial record", "Default parameters"],
        ),
        FormulaExplorerEntry(
            id="PRE-01",
            formula_name="Planning Readiness - Readiness Scoring Logic",
            source_module="Planning Readiness",
            mathematical_formula="ReadinessScore = 100.0 - (MissingMasters * 5.0 + MissingParameters * 3.0)",
            business_description="Evaluates whether a plant meets data completeness criteria for downstream planning execution.",
            required_inputs=["Plant code", "PlantMaterial master list", "VendorMaterial mappings"],
            generated_outputs=["Planning readiness score", "Readiness state (READY / WARNING / BLOCKED)"],
        ),
        FormulaExplorerEntry(
            id="PRE-02",
            formula_name="Planning Readiness - Blocking & Warning Rules",
            source_module="Planning Readiness",
            mathematical_formula="State = BLOCKED if Score < 70.0 else (WARNING if Score < 90.0 else READY)",
            business_description="Blocks the Central Planning Orchestrator execution if the readiness score falls below the 70% threshold.",
            required_inputs=["ReadinessScore"],
            generated_outputs=["Pipeline execution permission flag (can_proceed)"],
        ),
        FormulaExplorerEntry(
            id="CIN-01",
            formula_name="Consumption Intelligence - Average Daily Consumption & StdDev",
            source_module="Consumption Intelligence",
            mathematical_formula="D_avg = (1 / N) * sum(Q_i), Sigma_demand = sqrt((1 / (N - 1)) * sum((Q_i - D_avg)^2))",
            business_description="Calculates mean daily consumption and standard deviation over a 30/90 day rolling window from SAP MB51 issue movements.",
            required_inputs=["ConsumptionHistory daily quantities Q_i", "Sample size N"],
            generated_outputs=["D_avg", "Sigma_demand"],
        ),
        FormulaExplorerEntry(
            id="CIN-02",
            formula_name="Consumption Intelligence - Consumption Variability & Trend Detection",
            source_module="Consumption Intelligence",
            mathematical_formula="CV = Sigma_demand / D_avg",
            business_description="Detects demand volatility. CV > 0.5 indicates high consumption variability requiring elevated safety stock buffers.",
            required_inputs=["D_avg", "Sigma_demand"],
            generated_outputs=["Coefficient of Variation (CV)", "Trend classification (STABLE / VOLATILE)"],
        ),
        FormulaExplorerEntry(
            id="IIN-01",
            formula_name="Inventory Intelligence - Planning Available Inventory & DOI",
            source_module="Inventory Intelligence",
            mathematical_formula="Inv_avail = UsablePhysicalStock + IncomingPOQty, DOI = Inv_avail / D_avg",
            business_description="Derives true available stock by combining physical unrestricted inventory with open incoming Purchase Orders, and computes Days of Inventory.",
            required_inputs=["UsablePhysicalStock", "IncomingPOQty", "D_avg"],
            generated_outputs=["Inv_avail", "Days of Inventory (DOI)"],
        ),
        FormulaExplorerEntry(
            id="RMPM-01",
            formula_name="RMPM Statistical Planning - Dual Lead Time & Safety Stock",
            source_module="RMPM Statistical Planning",
            mathematical_formula="SS_1 = Z * Sigma_demand * sqrt(LT_1), SS_2 = Z * Sigma_demand * sqrt(LT_2)",
            business_description="Computes dual safety stock targets for primary lead time (LT-1) and emergency lead time (LT-2) based on service level factor Z.",
            required_inputs=["Service level Z factor", "Sigma_demand", "LT_1 (Primary Lead Time)", "LT_2 (Express Lead Time)"],
            generated_outputs=["SS_1 (Safety Stock 1)", "SS_2 (Safety Stock 2)"],
        ),
        FormulaExplorerEntry(
            id="RMPM-02",
            formula_name="RMPM Statistical Planning - Trigger Levels & Material Status Tree",
            source_module="RMPM Statistical Planning",
            mathematical_formula="Trigger_1 = Inv_avail - (D_avg * LT_1) - SS_1, Trigger_2 = Inv_avail - (D_avg * LT_2) - SS_2",
            business_description="Evaluates stockout reorder trigger thresholds and classifies material status (NORMAL / REORDER / CRITICAL_REORDER / STOCKOUT).",
            required_inputs=["Inv_avail", "D_avg", "LT_1", "LT_2", "SS_1", "SS_2"],
            generated_outputs=["Trigger_1 level", "Trigger_2 level", "Material Status"],
        ),
        FormulaExplorerEntry(
            id="FC-01",
            formula_name="Forecasting Engine - Moving Average & WMAPE Evaluation",
            source_module="Forecasting Engine",
            mathematical_formula="Forecast_t = (1 / k) * sum(Actual_{t-i}), WMAPE = sum(|Actual_t - Forecast_t|) / sum(Actual_t)",
            business_description="Generates moving average demand forecasts and evaluates accuracy using Weighted Mean Absolute Percentage Error (WMAPE).",
            required_inputs=["Historical daily demand actuals", "Moving window k=14"],
            generated_outputs=["Forecasted daily demand", "WMAPE accuracy score", "Forecast confidence score"],
        ),
        FormulaExplorerEntry(
            id="REQ-01",
            formula_name="Requirement Resolution Engine - Hierarchy Resolution",
            source_module="Requirement Resolution Engine",
            mathematical_formula="FinalReq = IBP_Req if IBP else (MonthlySchedule / 22 if Schedule else (Forecast if Forecast else D_avg))",
            business_description="Resolves competing demand sources into one final daily planning requirement following strict business priority rules.",
            required_inputs=["IBP daily requirement", "Monthly schedule quantity", "Statistical forecast", "Historical D_avg"],
            generated_outputs=["Final daily planning requirement", "Resolution source rationale"],
        ),
        FormulaExplorerEntry(
            id="RMT-01",
            formula_name="RM Totality Planning Engine - Contribution Ratio",
            source_module="RM Totality Planning Engine",
            mathematical_formula="RM_Req = sum(FG_Family_Requirement_j * TotalityRatio_j)",
            business_description="Calculates total raw material requirement across finished goods product families using totality mapping instead of individual BOMs.",
            required_inputs=["Finished goods family demand", "RMTotalityMapping contribution ratio"],
            generated_outputs=["Consolidated Raw Material Requirement"],
        ),
        FormulaExplorerEntry(
            id="PMP-01",
            formula_name="PM Planning Engine - BOM Packaging Ratio & Override Logic",
            source_module="PM Planning Engine",
            mathematical_formula="PM_Req = FG_Requirement * (OverrideRatio if PMOverride exists else BOM_Ratio)",
            business_description="Computes packaging material requirements from BOM ratios, applying planner PM overrides when configured.",
            required_inputs=["FG Requirement", "BOM packaging ratio", "PMOverride ratio"],
            generated_outputs=["Packaging Material Requirement"],
        ),
        FormulaExplorerEntry(
            id="DEP-01",
            formula_name="Dependency Intelligence Engine - RM/PM Matrix",
            source_module="Dependency Intelligence Engine",
            mathematical_formula="DependencyMatrix(FG_i, Mat_j) = 1.0 if (Mat_j in Totality(FG_i) or Mat_j in BOM(FG_i)) else 0.0",
            business_description="Maps dependencies between finished goods and raw/packaging materials.",
            required_inputs=["Finished goods list", "Raw materials & packaging materials list"],
            generated_outputs=["FG to Material dependency matrix"],
        ),
        FormulaExplorerEntry(
            id="PRD-01",
            formula_name="Production Readiness Engine - Readiness Decision Tree",
            source_module="Production Readiness Engine",
            mathematical_formula="FG_Status = READY_TO_PRODUCE if (for all RM,PM: UsableStock >= RequiredQty) else BLOCKED",
            business_description="Evaluates if finished goods can be produced based on available raw and packaging material inventory.",
            required_inputs=["FG BOM & totality requirements", "Material usable physical stocks"],
            generated_outputs=["FG Production Readiness Status", "Blocking RM/PM counts"],
        ),
        FormulaExplorerEntry(
            id="PRC-01",
            formula_name="Procurement Recommendation Engine - Deficit & Priority Rules",
            source_module="Procurement Recommendation Engine",
            mathematical_formula="Deficit = max(0.0, (D_avg * Horizon) + SS_1 - Inv_avail), ProcurementDate = max(Today, ArrivalDate - LeadTime)",
            business_description="Converts planning deficits into recommended procurement orders with arrival dates and priority classifications.",
            required_inputs=["D_avg", "Horizon days=15", "SS_1", "Inv_avail", "Lead time days"],
            generated_outputs=["Recommended procurement quantity", "Recommended procurement date", "Priority"],
        ),
        FormulaExplorerEntry(
            id="DPA-01",
            formula_name="Dynamic Procurement Allocation Engine - Multi-Vendor Capacity Splitting",
            source_module="Dynamic Procurement Allocation Engine",
            mathematical_formula="VendorAlloc_k = min(RemainingDeficit, VendorCapacity_k), StorageCapCheck: Stock + Alloc <= StorageLimit",
            business_description="Dynamically splits recommended procurement order quantities across primary and secondary vendors respecting daily capacities and storage limits.",
            required_inputs=["Recommended procurement quantity", "Vendor daily capacities", "Plant storage limit"],
            generated_outputs=["Vendor allocation draft records", "Vehicle load & storage cap checks"],
        ),
    ]

    @classmethod
    def list_formulas(cls) -> list[FormulaExplorerEntry]:
        return cls._entries

    @classmethod
    def get_formula_by_id(cls, formula_id: str) -> FormulaExplorerEntry:
        for entry in cls._entries:
            if entry.id.lower() == formula_id.lower():
                return entry
        raise AppError("FORMULA_NOT_FOUND", f"Formula with ID '{formula_id}' not found.", 404)
