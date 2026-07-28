# Forecasting & Planning – SPIP v1.5

## Purpose

This document defines the planning workflow introduced in SPIP v1.5.

Forecasting methods from SPIP v1.0 remain unchanged. This version enhances how forecast data is consumed during planning.

---

# Planning Philosophy

Planning starts with Finished Goods (FG).

Forecast

↓

Finished Goods

↓

Bill of Material (BOM)

↓

RM / PM Requirement

↓

Inventory Validation

↓

Planning

↓

Allocation

---

# Forecast Ownership

Forecasts shall only be maintained for Finished Goods.

Raw Material and Packaging Material demand shall be automatically derived using BOM relationships.

---

# BOM Explosion

Material requirements shall be calculated by exploding the Finished Good BOM.

Example:

FG-1001 Forecast = 100 Units

BOM

RM-A = 2

RM-B = 3

PM-A = 1

Required Quantity

RM-A = 200

RM-B = 300

PM-A = 100

---

# Planning Validation

Planning shall validate:

- Current Inventory
- Planning Availability
- Safety Stock
- Lead Time
- Material Criticality

---

# Production Risk

Planning shall identify:

- Material shortages
- Affected Finished Goods
- Estimated production impact

---

# Existing Forecast Models

The forecasting algorithms implemented in SPIP v1.0 remain valid.

Future ML enhancements shall extend—not replace—the existing forecasting framework.

---

# Future Scope (V2)

- Machine Learning Forecasting
- AI Demand Prediction
- Forecast Explainability
- What-if Simulation