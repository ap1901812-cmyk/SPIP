# 11 — Implementation Plan

## SPIP

**Purpose:** Build the enterprise-grade system in controlled phases inside one Git repository.

## Phase 0 — Specification Review
Claude reads `CLAUDE.md`, validates document consistency and reports blockers before coding.

## Phase 1 — Repository & Foundation
Create backend/frontend structure, configuration, Docker development setup, PostgreSQL connection, migrations, logging, testing and CI foundation.

## Phase 2 — Security Foundation
Authentication, RBAC, secrets/config, validation, rate limiting, safe errors, audit foundation and security tests.

## Phase 3 — Data Model & Integration
Implement plants, materials, vendors, consumption, inventory, PO/incoming supply and import framework for SAP plus Excel/CSV.

Use an `SAPAdapterInterface` and normalized records. Implement `MockSAPAdapter` as the default demo mode; real SAP connectivity is a deferred external dependency that can replace the adapter without rewriting planning logic.

## Phase 4 — Business/Planning Engine
Implement validated statistics, V1 safety stock, Planning Availability, requirement and ROP-based criticality rules with extensive unit tests.

Do not invent unresolved business thresholds.

## Phase 5 — Forecasting
Implement baseline, candidate-model framework, time-aware backtesting, model selection, fallback and monitoring metadata.

## Phase 6 — Allocation & Approval
Implement vendor allocation, edit exclusion, concurrency protection, manager approval/rejection and audit history.

## Phase 7 — Notifications
Implement in-app notifications and SMTP-based email through a configurable email adapter. No SMTP credentials in source code.

## Phase 8 — Frontend
Implement/refine the familiar red-and-white workflow, dashboards, criticality colors, allocation/approval UX, notifications and admin screens.

## Phase 9 — Reporting & Operational Jobs
Reports, scheduled/background jobs, import status and forecast-job UX.

## Phase 10 — Scale & Hardening
Load balancing validation, shared rate limiting/cache, performance testing, security scanning, backup/recovery and observability.

## Phase 11 — Release Candidate
Full E2E/regression testing, documentation check, dependency audit, secret scan, migration test and release tagging.

## Development Rule
Implement one approved ticket or tightly related ticket group at a time:
`Read context → Implement → Test → Review → Update tracker → Git commit`.

Do not ask Claude to regenerate the entire project after each phase.
