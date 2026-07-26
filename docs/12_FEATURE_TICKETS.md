# 12 — Feature Ticket List

## SPIP

**Purpose:** Provide an implementation backlog. Detailed acceptance criteria may be expanded when each ticket is started.

| ID | Feature | Priority | Depends On |
|---|---|---|---|
| FND-001 | Repository structure and configuration | P0 | — |
| FND-002 | Docker development environment | P0 | FND-001 |
| FND-003 | CI quality pipeline | P0 | FND-001 |
| DB-001 | PostgreSQL + Alembic foundation | P0 | FND-001 |
| OBS-001 | Structured logging/request IDs | P0 | FND-001 |
| SEC-001 | Authentication | P0 | DB-001 |
| SEC-002 | RBAC/permissions | P0 | SEC-001 |
| SEC-003 | Secure sessions/tokens | P0 | SEC-001 |
| SEC-004 | Distributed/configurable rate limiting | P0 | SEC-001 |
| SEC-005 | Strict API input validation | P0 | FND-001 |
| SEC-006 | Safe error handling | P0 | OBS-001 |
| SEC-007 | Secret/dependency scanning | P0 | FND-003 |
| SEC-008 | Secure file-upload controls | P0 | SEC-005 |
| DATA-001 | Plant/material/vendor models | P0 | DB-001 |
| DATA-002 | Consumption/inventory/PO models | P0 | DATA-001 |
| DATA-003 | Excel/CSV import pipeline | P1 | SEC-008, DATA-002 |
| DATA-004 | SAP adapter interface + default mock adapter | P1 | DATA-002 |
| PLAN-001 | Consumption statistics | P0 | DATA-002 |
| PLAN-002 | Configurable V1 safety-stock engine and lead-time fallback | P0 | PLAN-001 |
| PLAN-003 | Planning Availability/net-requirement engine | P0 | PLAN-002 |
| PLAN-004 | Deterministic ROP-based criticality engine | P0 | PLAN-003 |
| ML-001 | Forecast baseline | P0 | DATA-002 |
| ML-002 | Time-aware backtesting | P0 | ML-001 |
| ML-003 | Candidate model framework | P1 | ML-002 |
| ML-004 | Model selection/fallback | P1 | ML-003 |
| ML-005 | Forecast monitoring/version metadata | P1 | ML-004 |
| ALLOC-001 | Allocation create/edit logic | P0 | PLAN-003 |
| ALLOC-002 | Concurrency/over-allocation protection | P0 | ALLOC-001 |
| ALLOC-003 | Manager approval workflow | P0 | ALLOC-002, SEC-002 |
| NOTIF-001 | In-app notifications | P1 | SEC-002 |
| NOTIF-002 | Configurable SMTP email adapter | P1 | ALLOC-003 |
| API-001 | Core versioned REST APIs | P0 | Core backend tickets |
| FE-001 | Frontend foundation/design system | P0 | FND-001 |
| FE-002 | Dashboard/material planning views | P0 | API-001 |
| FE-003 | Forecast UX | P1 | ML-004, FE-001 |
| FE-004 | Allocation workflow UX | P0 | ALLOC-003, FE-001 |
| FE-005 | Manager approval UX | P0 | ALLOC-003, FE-001 |
| FE-006 | Notifications/admin UX | P1 | NOTIF-001, FE-001 |
| REP-001 | Reports/background report jobs | P1 | API-001 |
| OPS-001 | Background job infrastructure | P1 | FND-001 |
| OPS-002 | Shared cache/rate-limit infrastructure | P1 | SEC-004 |
| OPS-003 | Load-balancer/horizontal-scale validation | P1 | API-001, OPS-002 |
| QA-001 | Critical E2E workflow | P0 | Core feature completion |
| QA-002 | Performance/load tests | P1 | OPS-003 |
| QA-003 | Release security/regression gate | P0 | Core feature completion |
| REL-001 | v1.0 release candidate | P0 | QA-001, QA-003 |

### Ticket Rule
Each ticket implementation must reference only the relevant specifications, include acceptance criteria/tests, and update `PROJECT_TRACKER.md` after completion.

## Added Integration and Export Tickets

| ID | Feature | Priority | Depends On |
|---|---|---|---|
| REP-002 | Consolidated XLSX/CSV report export | P1 | REP-001, API-001 |
| REP-003 | Secure asynchronous export/download workflow | P1 | REP-002, OPS-001 |
| SAP-001 | Outbound SAP adapter contract and mock-mode integration | P1 | DATA-004 |
| SAP-002 | Approved SAP write-back workflow | P1 | SAP-001, ALLOC-003 |
| SAP-003 | SAP idempotency, acknowledgement, retry and audit | P1 | SAP-002, OBS-001 |
| QA-004 | Export and SAP write-back integration/security tests | P0 | REP-003, SAP-003 |
