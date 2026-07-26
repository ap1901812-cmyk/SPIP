# 13 — Project Tracker

## SPIP

**Purpose:** Living implementation status. Update this file after approved work is completed.

Status values: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `DONE`.

| Phase | Status | Notes |
|---|---|---|
| Specification review | DONE | Planning-rule decisions recorded; application implementation not started |
| Foundation | DONE | FastAPI/React foundation, Docker, logging, health API and CI pipeline |
| Security | DONE | User/Role models, PBKDF2 hashing, JWT tokens, RBAC dependencies, audit log & rate limiter |
| Database/Data Integration | NOT STARTED | Mock SAP adapter planned; real connectivity deferred external dependency |
| Business/Planning Engine | NOT STARTED | ROP criticality and V1 safety-stock policy defined |
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
- Planning Availability and deterministic ROP-based criticality are approved.
- Safety-stock V1 uses configurable ABC-class defaults and lead-time fallback.
- Demo SAP mode uses a mock adapter; real SAP connectivity is deferred.

## Added Capability Tracking

| Capability | Status | Notes |
|---|---|---|
| Consolidated Excel/CSV export | NOT STARTED | Filter-aware, RBAC-controlled; async for large reports |
| Outbound SAP adapter | NOT STARTED | Mock adapter default; real transport deferred behind contract |
| Controlled SAP write-back | NOT STARTED | Validated, authorized, auditable and idempotent |
| SAP acknowledgement/retry | NOT STARTED | Track success/failure/reference and notify on failures |
