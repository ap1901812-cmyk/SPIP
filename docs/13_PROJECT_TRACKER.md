# 13 — Project Tracker

## SPIP

**Purpose:** Living implementation status. Update this file after approved work is completed.

Status values: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `DONE`.

| Phase | Status | Notes |
|---|---|---|
| Specification review | NOT STARTED | Claude must review docs before coding |
| Foundation | NOT STARTED | |
| Security | NOT STARTED | |
| Database/Data Integration | NOT STARTED | SAP mechanism partially unknown |
| Business/Planning Engine | NOT STARTED | Some legacy thresholds require validation |
| Forecasting/ML | NOT STARTED | Designed for ~2–6 months history initially |
| Allocation/Approval | NOT STARTED | Manager approval required |
| Notifications | NOT STARTED | In-app + SMTP |
| Frontend | NOT STARTED | Preserve workflow; improve red/white UI |
| Reporting/Jobs | NOT STARTED | |
| Scale/Hardening | NOT STARTED | Includes load balancing |
| Release Candidate | NOT STARTED | |

## Known Decisions
- PostgreSQL retained.
- Multi-plant capable.
- Roles: Admin, Planner, Procurement, Manager/Approver, Read-only.
- Manager approval required for vendor allocations.
- SAP + Excel/CSV data ingestion.
- SMTP email plus in-app notifications.
- Demo enterprise-grade deployment; no organization name in product documentation.
- Historical demand availability initially assumed around 2–6 months.

## Added Capability Tracking

| Capability | Status | Notes |
|---|---|---|
| Consolidated Excel/CSV export | NOT STARTED | Filter-aware, RBAC-controlled; async for large reports |
| Outbound SAP adapter | NOT STARTED | Exact SAP transport remains configurable/unknown |
| Controlled SAP write-back | NOT STARTED | Validated, authorized, auditable and idempotent |
| SAP acknowledgement/retry | NOT STARTED | Track success/failure/reference and notify on failures |
