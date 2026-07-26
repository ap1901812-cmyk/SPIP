# 15 — Reference System Analysis

## Supply Planning Intelligence Platform (SPIP)

**Purpose:** Capture the useful functional behavior of the uploaded legacy RMPM application so SPIP can preserve its business journey without copying its weak implementation or visual design.

> **Reference rule:** The legacy project is a functional reference only. SPIP specifications (01–14) define the target system. If legacy code conflicts with approved security, business, architecture, or UX requirements, the approved SPIP specification wins.

## 1. Legacy System Shape

The reference application is a full-stack supply-planning application with:

- React + TypeScript + Vite frontend;
- FastAPI + SQLAlchemy backend;
- PostgreSQL persistence;
- SAP/enterprise synchronization services;
- Excel/CSV import/export;
- vendor allocation and SMTP email;
- material/vendor master management;
- allocation history and dispatch/calendar tracking.

The codebase contains useful workflows, but also prototype/POC patterns, duplicated logic, inconsistent API behavior and security gaps. It must not be copied wholesale.

## 2. Existing Frontend Navigation

The current SPA exposes these main areas:

1. **Dashboard**
2. **Allocation**
3. **Order/Allocation History**
4. **Dispatch Calendar**
5. **Material Master**

The sidebar also provides theme switching and sign-out.

SPIP should preserve the recognizable business journey, but navigation may be reorganized where it materially improves usability and role separation.

## 3. Login / User Entry

Legacy behavior:
- user selects Manager or Employee;
- enters username/password;
- backend verifies username/password/selected role;
- frontend stores basic role/name information locally.

### Enterprise treatment — REPLACE
Preserve the concept of role-aware access, but replace the implementation with the approved SPIP authentication, RBAC, secure session/token, rate-limit and audit requirements.

Target roles are:
- Admin
- Planner
- Procurement
- Manager/Approver
- Read-only

The user should not manually choose a role to gain access; authorization should come from the authenticated account.

## 4. Dashboard Workflow

The legacy dashboard:
- loads available analysis dates;
- lets the user select a reporting date;
- loads material inventory/planning results;
- shows KPI cards such as total items, critical actions, in-transit and in-stock;
- supports material-type and status filters;
- can hide zero-stock items;
- shows status distribution and top requirements;
- can trigger the consumption-analysis process;
- supports refresh/last-updated information.

Legacy criticality is derived from stock/requirement/safety-stock-style outputs and status text such as:
- In Stock
- Check material in Transit
- Raise Additional PO / Check Open PO

### Enterprise treatment — REFINE
Preserve:
- date-aware planning view;
- KPI summary;
- material status filtering;
- drill-down into critical materials;
- analysis/refresh visibility.

Improve:
- replace ambiguous status text with explicit Critical / Warning / Healthy states plus reason;
- add plant context;
- add forecast/safety-stock/coverage context;
- add data-freshness and source-quality indicators;
- use server-authoritative calculations;
- provide accessible charts and clearer table drill-down.

## 5. Allocation Workflow

The reference allocation screen supports:
- report date;
- material search;
- vendor search;
- plant filter;
- full-PO filter;
- PO synchronization;
- Excel/CSV upload;
- Material view and Vendor view;
- open-PO quantities;
- allocation draft quantity/date entry;
- editing existing draft allocations;
- local balance calculation;
- selecting draft allocations;
- emailing selected allocations to a vendor;
- Excel export.

### Core business journey to preserve
`Planning requirement → identify material/vendor/PO → enter allocation → validate capacity → save draft → review → communicate → track status`.

### Enterprise treatment — REFINE / CORRECT
Preserve:
- material-centric and vendor-centric ways to inspect allocation;
- PO-level context;
- plant visibility;
- draft editing;
- remaining/balance visibility;
- bulk actions where useful.

Change:
- manager approval must occur before final vendor communication;
- allocation validation must be authoritative in backend/database transactions;
- frontend balance is preview only;
- concurrent allocation must be protected;
- alerts should become structured inline/toast feedback;
- email sending must be an auditable workflow state;
- use clear Draft → Pending Approval → Approved/Rejected → Communicated lifecycle.

## 6. Allocation Editing Rule

The reference backend correctly attempts to exclude the allocation currently being edited when calculating used PO quantity.

This business concept must be preserved:

`Other allocations = active allocations - current allocation being edited`

This prevents the current allocation from competing against itself.

### Enterprise treatment — PRESERVE + TEST
Implement in the authoritative backend and add concurrency/regression tests.

## 7. Vendor Communication

Legacy behavior:
- selected allocations can be grouped by vendor;
- To/CC/BCC and a note can be supplied;
- SMTP email is generated with a delivery schedule table;
- allocation status changes to a mailed/communicated state;
- reminders can be sent.

### Enterprise treatment — REFINE
Preserve vendor email and reminders, but:
- require manager approval first;
- use configurable SMTP infrastructure;
- keep credentials server-side;
- use background jobs where appropriate;
- record communication attempts/results;
- prevent duplicate sends through idempotency where necessary;
- provide in-app notification/status feedback.

## 8. Allocation History

The reference system maintains allocation history with fields such as:
- material;
- vendor;
- allocated quantity;
- received quantity;
- target date;
- status;
- last updated.

It also supports status filtering, reminders, cancellation/receipt-related actions and per-allocation logs.

### Enterprise treatment — PRESERVE + REFINE
Keep an auditable timeline. SPIP should make status, approval, communication, receipt and exception history easier to inspect.

## 9. Dispatch Calendar

The legacy Dispatch screen is a monthly allocation/delivery calendar with:
- previous/next/today navigation;
- status filters;
- per-day allocation counts;
- day drill-down;
- search by material/vendor/PO;
- statuses such as Draft, Mailed, Confirmed, Received, Cancelled and Pending.

### Enterprise treatment — PRESERVE CONCEPT
Keep calendar-based delivery visibility, but align statuses with the approved SPIP workflow and use consistent terminology across dashboard, allocation, history and notifications.

## 10. Material Master

The reference Material Master supports:
- material search;
- create/edit/delete material;
- UOM and planning parameters;
- linking/unlinking vendors;
- vendor lead time;
- vendor capacity per trip.

### Enterprise treatment — PRESERVE + SECURE
Keep master-data management, but restrict actions by RBAC, validate all values, audit changes and support plant-specific configuration where business rules require it.

## 11. SAP / File Data Flow

The reference backend contains separate services for:
- PO synchronization;
- receipt/GRN synchronization;
- database synchronization;
- report/consumption processing;
- Excel/CSV upload.

The exact enterprise SAP connection mechanism is not fully established.

Legacy reports such as MB51, MB5B, ME2N, ZIBP and ZRMRP are reference data sources only; they do not define guaranteed production SAP interfaces.

### Enterprise treatment — REFINE
Use a defined integration adapter boundary:

`SAP / Excel / CSV → ingestion adapter → validation → normalized database records → planning engine`

Planning logic must not depend directly on a specific SAP transport mechanism.

## 12. Planning / Reporting Logic

The reference backend generates consumption-analysis and final-output reports. It contains:
- rolling consumption/statistical calculations;
- safety-stock-related calculations;
- material status determination;
- report generation;
- fallback file-based dashboard behavior.

### Enterprise treatment — DO NOT COPY BLINDLY
`02_BUSINESS_RULES_AND_MATHEMATICS.md` is authoritative. Legacy formulas are evidence of intended behavior, not proof of correctness.

Known legacy concepts requiring validation include:
- 7-day rolling statistics;
- Max − SD;
- Average + SD;
- fixed Z around 1.65;
- approximately 12-day forecast horizon;
- exact criticality thresholds.

## 13. Useful Data Concepts Found in the Reference

Useful entities/fields include:
- Material
- Vendor
- Material–Vendor relationship
- Vendor lead time
- Vendor capacity per trip
- Material planning parameters
- Purchase Order
- Allocation Order
- Goods Receipt
- Allocation Log
- User
- target delivery date
- received quantity
- user remarks
- plant
- PO number

SPIP may refine or normalize these structures according to `06_DATABASE_DESIGN.md`.

## 14. Reference Implementation Problems Not to Carry Forward

The new project must not reproduce these prototype patterns:

- frontend role state used as if it were authentication;
- login endpoint without a complete protected-API authorization chain;
- unrestricted CORS;
- hardcoded localhost API URL;
- API keys exposed/configured in frontend code paths;
- browser `alert()` as primary error UX;
- duplicated/uncertain API calls;
- mock data mixed with real application state;
- large duplicated report-service code;
- duplicate schema/service variants;
- file-system reports used as an application source of truth;
- broad exception swallowing / print-based debugging;
- frontend-only or mismatched validation;
- inconsistent status terminology;
- direct long-running processing in request paths where background work is more appropriate.

## 15. Legacy Feature Classification

| Legacy Capability | SPIP Decision |
|---|---|
| Dashboard planning overview | PRESERVE + REDESIGN |
| Date-based analysis | PRESERVE |
| KPI/status cards | PRESERVE + IMPROVE |
| Material/vendor filters | PRESERVE |
| Material-centric allocation | PRESERVE |
| Vendor-centric allocation | PRESERVE |
| Plant filter | PRESERVE / EXPAND |
| PO synchronization | PRESERVE behind adapter |
| Excel/CSV import | PRESERVE + SECURE |
| Draft allocation | PRESERVE |
| Edit-current-allocation exclusion | PRESERVE + TEST |
| Direct draft-to-email flow | REPLACE with manager approval |
| SMTP vendor communication | PRESERVE + HARDEN |
| Reminders | PRESERVE |
| Allocation history/logs | PRESERVE + IMPROVE |
| Dispatch calendar | PRESERVE CONCEPT |
| Material/vendor master | PRESERVE + RBAC |
| Manager/Employee role selector | REPLACE |
| Existing visual design | REFERENCE ONLY |
| Existing auth/security | REPLACE |
| Existing report math | VALIDATE against Business Rules |
| Frontend Gemini API-key integration | REMOVE unless separately approved |

## 16. Target Business Journey

The enterprise SPIP journey should become:

`Secure login → role/plant-aware dashboard → validated planning data → forecast + safety stock + criticality → planner allocation draft → manager approval → vendor communication → dispatch/receipt tracking → history/audit/reporting`

This is the primary workflow Claude should preserve while implementing the enterprise specifications.

## 17. Priority Rule for Claude

When implementing SPIP:
1. use the reference system to understand **what users are trying to accomplish**;
2. use SPIP specifications to decide **how it must be implemented**;
3. do not copy legacy code or UI merely because it exists;
4. preserve useful workflows only when they do not conflict with approved SPIP requirements.

## Enterprise Extension: Export and SAP Write-Back

The reference system contains report/file export concepts and SAP synchronization-related services. SPIP formalizes these as enterprise capabilities rather than copying the legacy implementation.

- Consolidated planning reports shall support XLSX/CSV download.
- SAP integration shall support an outbound adapter for approved write-back where the real enterprise interface permits it.
- The exact SAP protocol is intentionally unresolved until the actual environment is known.
- Outbound writes require validation, authorization, idempotency, status tracking and auditability.
- Forecast/ML predictions do not directly write procurement changes to SAP.
