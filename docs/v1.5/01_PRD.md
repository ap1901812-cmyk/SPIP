# Product Requirements Document (PRD) – SPIP v1.5

## Document Information

| Item | Value |
|------|------|
| Product | Supply Planning Intelligence Platform (SPIP) |
| Version | 1.5 |
| Based On | SPIP v1.0 |
| Status | Draft |
| Owner | Product Team |

---

# Purpose

SPIP v1.5 enhances the existing SPIP platform by introducing enterprise-grade planning capabilities while preserving the current architecture and business logic.

This version focuses on improving planning accuracy, material visibility, dependency analysis, and decision support without changing the core purpose of the application.

---

# Business Problem

The current SPIP version successfully performs inventory planning and allocation but has several limitations:

- Planning is material-centric rather than Finished Good (FG) centric.
- RM and PM dependencies are not clearly visible.
- Users cannot easily determine production impact caused by material shortages.
- Dashboard provides limited planning intelligence.

---

# Objectives

The primary objectives of SPIP v1.5 are:

- Introduce Finished Goods driven planning.
- Separate Finished Goods, Raw Materials and Packaging Materials logically.
- Introduce Bill of Material (BOM) relationships.
- Improve planning transparency.
- Improve production risk visibility.
- Enhance dashboard intelligence.
- Maintain backward compatibility.

---

# In Scope

- FG Workspace
- BOM Management (Read Only)
- RM & PM Dependency Tracking
- Production Risk Analysis
- Dashboard Enhancement
- Planning Engine Enhancement
- Reporting Improvements

---

# Out of Scope

The following modules remain outside the scope of SPIP.

- Procurement
- Purchase Orders
- Warehouse Operations
- Manufacturing Execution
- Finance
- HR
- ERP Replacement

SAP continues to remain the System of Record.

---

# Target Users

- Supply Chain Planner
- Inventory Planner
- Production Planner
- Business Manager
- Management

---

# Success Criteria

SPIP v1.5 will be considered successful when:

- Existing V1 functionality remains operational.
- New planning workflow supports FG-driven planning.
- Material dependencies are visible.
- Production impact is traceable.
- Dashboard provides actionable planning insights.
- No breaking API changes are introduced.

---

# High Level Features

| Feature | Status |
|---------|--------|
| FG Workspace | New |
| BOM Integration | New |
| Dependency Tracking | New |
| Production Risk | New |
| Dashboard Enhancement | New |
| Planning Engine Enhancement | Enhanced |
| Reports | Enhanced |

---

# Version Comparison

| Capability | V1 | V1.5 |
|------------|----|------|
| Inventory Planning | ✓ | ✓ |
| Allocation | ✓ | ✓ |
| Forecast | ✓ | ✓ |
| FG Workspace | ✗ | ✓ |
| BOM | ✗ | ✓ |
| Dependency Tracking | ✗ | ✓ |
| Production Risk | ✗ | ✓ |
| Enhanced Dashboard | ✗ | ✓ |

---

# References

- SPIP V1 PRD
- Business Rules Document
- System Architecture
- Database Design
- Reference System Analysis
