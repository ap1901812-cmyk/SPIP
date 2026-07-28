# Business Rules & Mathematics – SPIP v1.5

## Purpose

This document defines the additional business rules introduced in SPIP v1.5. Existing business rules from SPIP v1.0 remain valid unless explicitly modified here.

---

# Planning Philosophy

Planning begins with Finished Goods demand.

Planning Flow

Forecast
↓

Finished Goods
↓

Bill of Material (BOM)
↓

Raw Material & Packaging Material Requirements
↓

Inventory Planning
↓

Allocation

---

# Material Classification

Every material shall belong to one of the following categories.

- Finished Good (FG)
- Raw Material (RM)
- Packaging Material (PM)

This classification is mandatory for all planning activities.

---

# BOM Rule

Every Finished Good may contain one or more RM and PM components.

BOM shall remain read-only within SPIP.

SAP is the master source for BOM data.

---

# Forecast Rule

Forecasts are generated only for Finished Goods.

RM and PM demand shall be derived using BOM explosion.

---

# Planning Rule

Required Material Quantity

= FG Forecast × BOM Quantity

---

# Inventory Rule

Planning shall consider:

- Current Stock
- Safety Stock
- Lead Time
- Planning Availability

Existing V1 planning formulas remain unchanged.

---

# Criticality Rule

Material status:

- Healthy
- Warning
- Critical

Existing planning availability logic remains valid.

---

# Dependency Rule

Every RM and PM must maintain a "Where Used" relationship.

Users must be able to identify:

- affected FG
- production impact
- dependency count

---

# Production Risk Rule

Production Risk shall be calculated using:

- Forecast
- BOM
- Available Inventory
- Critical Materials

---

# Explainability Rule

Every Critical status must include an explanation.

Example:

RM-102 is Critical because available inventory is below required quantity for FG-1005.

---

# Future Scope

The following remain part of SPIP V2:

- ML-based planning
- Material substitution
- What-if simulation
- Supplier risk scoring
