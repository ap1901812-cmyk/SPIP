# System Architecture – SPIP v1.5

## Purpose

SPIP v1.5 extends the current architecture without replacing existing modules.

---

# Architecture Overview

```
Forecast
    │
    ▼
Finished Goods
    │
    ▼
Bill of Material
    │
    ▼
RM / PM Requirements
    │
    ▼
Inventory Planning
    │
    ▼
Allocation
    │
    ▼
SAP
```

---

# Existing Components

The following modules remain unchanged.

- Authentication
- Inventory
- Forecasting
- Allocation
- Reporting
- Notification

---

# New Components

SPIP v1.5 introduces:

- FG Workspace
- BOM Service
- Dependency Service
- Production Risk Engine

---

# Data Flow

1. Forecast is created for FG.
2. BOM determines RM/PM requirements.
3. Inventory availability is evaluated.
4. Planning engine calculates shortages.
5. Dashboard displays production impact.
6. Allocation recommendations are generated.

---

# Integration

SAP remains responsible for:

- Material Master
- BOM
- Plant Master
- Transactions

SPIP remains responsible for:

- Planning
- Analytics
- Risk Identification
- Reporting

---

# Design Principles

- Extend existing modules.
- Do not duplicate SAP functionality.
- Keep services loosely coupled.
- Maintain modular architecture.

---

# Future Architecture (V2)

Future services may include:

- AI Planning Engine
- Scenario Simulator
- Supplier Analytics
- Capacity Planning