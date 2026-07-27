# 13 Ã¢â‚¬â€ Project Tracker

## SPIP

**Purpose:** Living implementation status. Update this file after approved work is completed.

Status values: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `DONE`.

| Phase | Status | Notes |
|---|---|---|
| Specification review | DONE | Planning-rule decisions recorded; application implementation not started |
| Foundation | DONE | FastAPI/React foundation, Docker, logging, health API and CI pipeline |
| Security | DONE | User/Role models, PBKDF2 hashing, JWT tokens, RBAC dependencies, audit log & rate limiter |
| Database/Data Integration | DONE | Multi-plant schema, CSV ingestion, SAPAdapterInterface & MockSAPAdapter demo mode |
| Business/Planning Engine | DONE | V1 Safety Stock, Planning Availability (AI), ROP and deterministic Criticality engine |

| Forecasting/ML | DONE | Time-aware backtesting framework, candidate model selection & fallback |

| Allocation/Approval | DONE | V1 lifecycle (DRAFT, PENDING_APPROVAL, APPROVED, REJECTED), current-edit exclusion & Manager approval |
| Notifications | DONE | In-app persistent notification model, API, RBAC isolation, business event triggers, and SMTP/mock email adapter |
| Frontend | DONE | Enterprise Red & White UI, AuthContext, Dashboard, Planning Detail, Forecasting, Allocations & Manager Queue |

| Reporting/Jobs | DONE | Phase 9: Consolidated CSV and openpyxl XLSX export service, filters, and frontend Reports Center |
| Operational Jobs | DONE | Phase 10: PostgreSQL JobRun persistence (migration 005), job lifecycle, concurrency locking, retry API, durable report artifacts |
| Release Candidate | NOT STARTED | Scheduled for Phase 11 |

## Known Decisions
- PostgreSQL retained.
- Multi-plant capable.
- Roles: Admin, Planner, Procurement, Manager/Approver, Read-only.
- Manager approval required for vendor allocations.
- SAP + Excel/CSV data ingestion.
- SMTP email plus in-app notifications.
- Demo enterprise-grade deployment; no organization name in product documentation.
- Historical demand availability initially assumed around 2Ã¢â‚¬â€œ6 months.
- Planning Availability and deterministic ROP-based criticality are approved.
- Safety-stock V1 uses configurable ABC-class defaults and lead-time fallback.
- Demo SAP mode uses a mock adapter; real SAP connectivity is deferred.

## Added Capability Tracking

| Capability | Status | Notes |
|---|---|---|
| Consolidated Excel/CSV export | NOT STARTED | Filter-aware, RBAC-controlled; async for large reports |
| Outbound SAP adapter | DONE | Mock adapter default with write_back_allocation contract |
| Controlled SAP write-back | DONE | Validated, authorized, auditable and idempotent |
| SAP acknowledgement/retry | NOT STARTED | Track success/failure/reference and notify on failures |
