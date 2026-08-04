# SPIP V2 -- Business Requirements Document (BRD)

# Part 2 -- Planning & Procurement Intelligence

## 12. Consumption Intelligence

### Purpose

Transform historical consumption into planning intelligence.

### Business Requirements

-   Analyze historical material consumption.
-   Calculate daily, weekly and monthly consumption trends.
-   Support planning for every plant independently.
-   Provide inputs to forecasting and statistical planning.

### Inputs

-   Consumption Data
-   Plant
-   Material
-   Posting Date

### Outputs

-   Consumption trend
-   Average consumption
-   Consumption variability

------------------------------------------------------------------------

## 13. Inventory Intelligence

### Purpose

Provide an accurate inventory position before planning begins.

### Business Requirements

-   Calculate available inventory.
-   Consider current stock, open purchase orders and gate entries.
-   Support plant-wise inventory visibility.

### Outputs

-   Available Inventory
-   Incoming Inventory
-   Inventory Availability

------------------------------------------------------------------------

## 14. RMPM Statistical Planning Engine

### Purpose

Provide the statistical planning foundation for SPIP V2.

### Business Requirement

SPIP V2 shall adopt the statistical planning methodology implemented in
the RMPM project **without modification**.

The following business logic shall remain identical to RMPM: - Lead Time
1 - Lead Time 2 - Safety Stock 1 - Safety Stock 2 - Trigger 1 - Trigger
2 - Material Status Logic

SPIP V2 will consume the outputs of this engine rather than redefine its
calculations.

------------------------------------------------------------------------

## 15. Forecasting Engine

### Purpose

Estimate future material demand.

### Business Requirements

-   Default forecasting model: Moving Average.
-   Support WMAPE-based model evaluation.
-   Continuously improve forecasting as new historical data becomes
    available.
-   Display forecast confidence.

------------------------------------------------------------------------

## 16. Requirement Resolution Engine

### Purpose

Generate the final planning requirement.

### Inputs

-   Forecast
-   Historical Consumption
-   IBP Planning Data
-   Monthly Requirement

### Output

Final Planning Requirement

------------------------------------------------------------------------

## 17. Raw Material Planning Engine

### Purpose

Estimate RM requirements without depending on an exact BOM.

### Business Requirements

-   Use RM Totality Mapping.
-   Use historical consumption.
-   Use dependency relationships.
-   Allow planner validation.

------------------------------------------------------------------------

## 18. Packaging Material Planning Engine

### Business Requirements

-   Use BOM as the default PM source.
-   Allow planner override where necessary.
-   Maintain editable PM relationships.

------------------------------------------------------------------------

## 19. Dependency Intelligence Engine

### Purpose

Identify the production impact of RM and PM shortages.

### Business Requirements

-   Show RM → FG dependency.
-   Show PM → FG dependency.
-   Display affected Finished Goods.
-   Support impact analysis.

------------------------------------------------------------------------

## 20. Production Readiness Engine

### Purpose

Determine whether a Finished Good can currently be produced.

### Statuses

-   Ready to Produce
-   RM Shortage
-   PM Shortage
-   Production Blocked

### Outputs

-   RM Availability
-   PM Availability
-   Blocking Materials
-   Recommended Action

------------------------------------------------------------------------

## 21. Planning Engine

### Purpose

Generate material planning outputs.

### Outputs

-   Gross Requirement
-   Net Requirement
-   Material Criticality

------------------------------------------------------------------------

## 22. Proactive Planning Engine

### Purpose

Generate a rolling 15-day procurement plan automatically.

### Business Requirements

-   Run after every successful planning cycle.
-   Consider inventory, RMPM planning outputs, vendor capacity, vehicle
    capacity, storage capacity, open purchase orders and gate entries.
-   Produce procurement recommendations before shortages occur.

------------------------------------------------------------------------

## 23. Reactive Planning Engine

### Purpose

Respond to unexpected planning events.

### Business Requirements

-   Handle emergency demand.
-   Handle vendor delays.
-   Handle sudden consumption changes.
-   Generate immediate procurement recommendations.

------------------------------------------------------------------------

## 24. Procurement Recommendation Engine

### Outputs

-   Recommended Quantity
-   Recommended Vendor
-   Procurement Date
-   Priority
-   Business Reason

------------------------------------------------------------------------

## 25. Dynamic Procurement Allocation Engine

### Business Requirements

-   Recommend vendor allocations.
-   Consider vendor capacity.
-   Consider vehicle capacity.
-   Consider storage constraints.
-   Allow planner review and editing.
-   Support vendor notification after approval.
