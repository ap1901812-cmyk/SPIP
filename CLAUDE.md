# CLAUDE.md — SPIP Development Contract

This repository contains the Supply Planning Intelligence Platform (SPIP), an enterprise-grade rebuild of an existing RMPM planning application.

## Before Coding
1. Read this file.
2. Read `13_PROJECT_TRACKER.md`.
3. Read only the specifications relevant to the current ticket.
4. Inspect existing code and tests before modifying anything.
5. Report blockers/ambiguities instead of inventing business rules.

## Document Routing
- Product/scope → `01_PRD`
- Planning formulas → `02_BUSINESS_RULES_AND_MATHEMATICS`
- Security → `03_SECURITY_AND_ACCESS_CONTROL`
- Technology → `04_TRD`
- Architecture/load balancing → `05_SYSTEM_ARCHITECTURE`
- Database → `06_DATABASE_DESIGN`
- APIs → `07_API_SPECIFICATION`
- Frontend/UX → `08_FRONTEND_SPECIFICATION`
- Forecasting/ML → `09_FORECASTING_AND_ML_SPECIFICATION`
- Testing → `10_TESTING_AND_QA_STRATEGY`
- Build order → `11_IMPLEMENTATION_PLAN`
- Work items → `12_FEATURE_TICKETS`
- Current status → `13_PROJECT_TRACKER`
- Future changes/debugging → `14_MAINTENANCE_AND_CHANGE_MANAGEMENT`


- Legacy/reference behavior → `docs/15_REFERENCE_SYSTEM_ANALYSIS.md`
- Target UI/UX design → `docs/16_UI_UX_DESIGN_BLUEPRINT.md`

## Non-Negotiable Rules
- Do not rewrite working modules unnecessarily.
- Do not invent unresolved business thresholds.
- Do not weaken security controls.
- Backend is authoritative for business validation/calculations.
- Database changes require migrations.
- Bug fixes require regression tests where practical.
- Never commit secrets or real sensitive enterprise data.
- Preserve multi-plant capability.
- Vendor allocation requires manager approval.
- Forecasting must have baseline/fallback behavior.
- Keep the familiar simple UI workflow and improve UX rather than replacing it arbitrarily.
- Run relevant tests before marking a ticket Done.
- Update the tracker after completed work.

## Implementation Workflow
`Ticket → Relevant docs → Inspect code → Implement → Test → Review → Tracker → Git commit`.

Do not attempt to regenerate the whole application for a single change.

## Reference Project Rule
The uploaded legacy RMPM application is a functional reference only. Preserve useful business journeys, but do not copy its UI, security weaknesses, prototype patterns, or code wholesale. For frontend work, read both `docs/15_REFERENCE_SYSTEM_ANALYSIS.md` and `docs/16_UI_UX_DESIGN_BLUEPRINT.md`.

## Export and SAP Write-Back Rules

- Consolidated report export in XLSX/CSV is an explicit SPIP capability.
- Apply backend RBAC and authorized plant/data scope to every export.
- Use background jobs for large exports.
- SAP integration is bidirectional through adapters; do not hardcode an unknown SAP protocol.
- Never let the frontend forward arbitrary SAP commands/payloads.
- Outbound SAP write-back must be validated, authorized, auditable and idempotent.
- Respect manager approval where required by the business workflow.
- Record acknowledgement/reference and handle retry/failure safely.
- ML/forecast output must never autonomously write business/procurement changes to SAP.
