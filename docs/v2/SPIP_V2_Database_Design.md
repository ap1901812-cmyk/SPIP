# SPIP V2 -- Database Design

## Purpose

Define the logical database structure for SPIP V2.

## Master Tables

-   Material Master
-   Vendor Master
-   Material Planning Parameters
-   RM Totality Mapping
-   PM Mapping
-   Vehicle Capacity

## Transaction Tables

-   Purchase Orders
-   Consumption
-   Stock
-   GRN
-   IBP Planning

## Planning Tables

-   Forecast
-   Statistical Planning Outputs
-   Procurement Recommendations
-   Vendor Allocations
-   Production Readiness

## Audit Tables

-   Notification History
-   Planner Overrides
-   Approval History

## Design Principles

-   Normalize master data.
-   Preserve auditability.
-   Support multi-plant planning.
-   Maintain referential integrity.
