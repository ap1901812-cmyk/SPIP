# Changelog

All notable SPIP changes should be recorded here.

Use semantic versions where practical.

## [Unreleased]
### Added
- Phase 10 Operational Jobs & Reliability (`OPS-001`, `OPS-002`, `OPS-003`).
- Durable `JobRun` ORM model (`job_runs` table) and Alembic migration `005_jobs_schema.py`.
- Operational Job management service (`app/services/jobs.py`) supporting `REPORT_EXPORT`, `SAP_SYNC`, `FORECAST_GENERATE`, and `PLANNING_RECALC` background job types with state transitions (`PENDING`, `RUNNING`, `COMPLETED`, `FAILED`), error tracking, and retry workflow (`retry_job`).
- Replaced Phase 9 in-memory `_export_cache` boundary with durable PostgreSQL `JobRun.binary_artifact` storage, guaranteeing report export artifacts survive backend process restarts.
- Concurrency & idempotency protection using database row locking (`with_for_update`) to prevent duplicate overlapping job executions.
- REST operational jobs API routes (`POST /api/v1/jobs`, `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`, `POST /api/v1/jobs/{job_id}/retry`).
- Focused backend test suite (`test_jobs.py`) proving job lifecycle, PostgreSQL artifact persistence, concurrency locking, and retry handling.
- Phase 9 Reporting & Export Engine (`REP-001`, `REP-002`, `REP-003`).
- Reporting service (`app/services/reporting.py`) reusing authoritative backend calculation engines (`evaluate_material_planning`, `generate_demand_forecast`, allocation queries) for `planning_summary`, `forecast_summary`, and `allocations` datasets.
- Standards-compliant UTF-8 CSV exporter (`build_csv_export`) and Excel workbook exporter (`build_xlsx_export` via `openpyxl`) with header styling and memory buffer streaming.
- Filter capabilities (`plant_code`, `material_code`, `criticality_status`, `status`) with error validation.
- REST reporting API routes (`GET /api/v1/reports`, `POST /api/v1/reports/exports`, `GET /api/v1/reports/exports/{export_id}/download`, `GET /api/v1/reports/download`).
- Phase 9 asynchronous export job boundary (`_export_cache` registry with job token security isolation).
- Dedicated frontend Reports & Exports Center (`ReportsPage.tsx`, sidebar nav item).
- Comprehensive reporting backend test suite (`test_reporting.py`).
- Phase 7 Notifications Engine (`NOTIF-001`, `NOTIF-002`, `FE-006`).
- In-app `Notification` database model and Alembic migration `004_notifications_schema.py`.
- Notification service (`app/services/notification/service.py`) supporting unread count, pagination, user recipient isolation, and mark read/all-read operations.
- Configurable SMTP / Mock Email Adapter boundary (`app/services/notification/email.py`) with secret isolation, deterministic local development mock mode, and graceful SMTP transport fallback.
- REST notification endpoints (`GET /api/v1/notifications`, `GET /api/v1/notifications/unread-count`, `PATCH /api/v1/notifications/{id}/read`, `POST /api/v1/notifications/mark-all-read`).
- Business event integration wiring notifications into allocation lifecycle events: `submit_allocation` (notifies Managers/Approvers & Admins), `approve_allocation` (notifies Planner), `reject_allocation` (notifies Planner with reason).
- Lightweight frontend Notification Center (`NotificationsPage.tsx`, navbar bell indicator with unread badge in `AppShell.tsx`, sidebar nav link).
- Comprehensive notification backend test suite (`test_notifications.py`).
- V1 Core Frontend + Backend Integration (`frontend/` connected to FastAPI endpoints).
- Enterprise Red & White Visual Design System (`src/styles/index.css`) with responsive layout, metric cards, status pills (`CRITICAL`, `WARNING`, `HEALTHY`), and modal dialogs.
- `AuthContext` & `useAuth` hook providing token storage in `localStorage`, `GET /auth/me` user profile sync, protected application routing, 401 handling, and role checks (`hasRole()`).
- `LoginPage` with credentials form and Quick Demo Preset buttons (Planner, Manager, Admin).
- `AppShell` with top header, current user & role badges, plant context filter, and sidebar navigation.
- `DashboardPage` featuring plant filter, summary metric cards (Total, Critical, Warning, Healthy), and interactive material planning table.
- `PlanningDetailPage` presenting all 17 audit trace components ($D, \sigma_d, LT, Z, SS, AI, ROP$, physical stock breakdown, incoming PO, committed allocations, and deterministic criticality rationale).
- `ForecastingPage` displaying candidate model metadata (`selected_model`, `evaluation_metric_value` WMAPE), historical window, fallback indicator, and day-by-day point forecast bar chart & table.
- `AllocationsPage` supporting real-time capacity checking against `Planning Availability`, allocation creation/editing, optimistic concurrency locking (`version`), and submission for approval.
- `ManagerApprovalPage` providing approval queue with outbound SAP write-back integration, mandatory rejection reason modal, and RBAC enforcement.
- `IngestionPage` enabling CSV/XLSX file uploads (`consumption`, `inventory`) and triggering full SAP adapter sync.
- Frontend test suite (`App.test.tsx`, `DashboardPage.test.tsx`) covering login rendering, protected routing, and dashboard metrics.
- Phase 6 Allocation & Manager Approval workflow (`ALLOC-001` through `ALLOC-003`, `SAP-002`, `SAP-003`).

- Database model `Allocation` (`DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`) and Alembic migration `003_allocations_schema.py`.
- Allocation service layer (`app/services/allocation.py`) enforcing capacity checks, optimistic concurrency locking (`version`), state transitions, and audit logging.
- **Current-Edit Exclusion Rule:** Implemented capacity validation during edits excluding current allocation instance to prevent double-subtraction false positives.
- Planning Availability integration: active committed allocations (`PENDING_APPROVAL`, `APPROVED`) reduce availability exactly once; non-consuming statuses (`DRAFT`, `REJECTED`) do not consume availability.
- Outbound SAP write-back integration contract (`write_back_allocation()`) generating synthetic SAP PO reference numbers in mock mode.
- Phase 6 REST endpoints (`POST /api/v1/allocations`, `GET /api/v1/allocations`, `PUT /api/v1/allocations/{id}`, `POST /api/v1/allocations/{id}/submit`, `POST /api/v1/allocations/{id}/approve`, `POST /api/v1/allocations/{id}/reject`).
- Phase 5 V1 Demand Forecasting (`ML-001` through `ML-005`).

- Candidate forecasting model hierarchy (`app/services/forecasting/models.py`) implementing `NaiveForecastModel`, `MovingAverageForecastModel` (7D/14D), and `ExponentialSmoothingForecastModel` ($\alpha=0.3$).
- Chronological time-series backtesting and metrics evaluation module (`app/services/forecasting/evaluation.py`) computing MAE, RMSE, and WMAPE without future data leakage.
- Forecasting engine orchestrator (`app/services/forecasting/engine.py`) executing candidate backtest selection (lowest WMAPE) or deterministic fallback for insufficient historical observations (< 5 records).
- Phase 5 REST endpoints (`GET /api/v1/forecasts/materials/{code}?plant_code=...`, `GET /api/v1/forecasts/summary`).
- Phase 4 Core Planning & Inventory Decision Engine (`PLAN-001` through `PLAN-004`).

- Consumption statistics module (`app/services/planning/statistics.py`) for rolling daily demand mean ($D$) and population standard deviation ($\sigma_d$).
- Ordered lead time resolution service (`app/services/planning/lead_time.py`) supporting primary vendor lead time, plant-material master, and default fallbacks.
- V1 Safety Stock engine (`app/services/planning/safety_stock.py`) implementing $SS = Z \times \sigma_d \times \sqrt{LT}$ with configurable ABC class Z-factors, min floors, max ceilings, and manual overrides.
- Planning Availability engine (`app/services/planning/availability.py`) implementing $AI = \text{usable} + \text{eligible\_incoming\_po} - \text{committed}$ with explicit double-subtraction prevention.
- Integrated Planning Engine Orchestrator (`app/services/planning/engine.py`) calculating $D \times LT$, $ROP = (D \times LT) + SS$, and deterministic criticality (`CRITICAL`, `WARNING`, `HEALTHY`) with explainable audit reasoning.
- Phase 4 REST endpoints (`GET /api/v1/planning/materials/{code}?plant_code=...`, `GET /api/v1/planning/summary`).
- Phase 3 Data Models, Ingestion & SAP Adapter foundation (DATA-001 through DATA-004, SAP-001).

- Multi-plant database models (`Plant`, `Material`, `PlantMaterial`, `Vendor`, `VendorMaterial`, `ConsumptionHistory`, `InventorySnapshot`, `PurchaseOrder`, `PurchaseOrderLine`).
- Alembic database migration `002_domain_schema.py` for all multi-plant domain entities.
- Abstract `SAPAdapterInterface` contract with `MockSAPAdapter` (multi-plant synthetic data generator) and `RealSAPAdapter` (deferred stub).
- Configurable SAP adapter factory (`get_sap_adapter()`) driven by `SAP_ADAPTER_MODE` environment configuration.
- Reusable CSV/Excel data ingestion service (`app/services/ingestion.py`) with row-level validation and error reporting.
- Phase 3 REST endpoints (`/plants`, `/materials`, `/vendors`, `/inventory`, `/consumption`, `/purchase-orders`, `/imports/csv`, `/sap/status`, `/sap/sync`).
- Phase 2 Security & Authentication foundation (SEC-001 through SEC-008).
- SQLAlchemy database models for `User`, `UserRole`, `RoleEnum` (Admin, Planner, Procurement, Manager/Approver, Read-only), and `AuditLog`.
- Secure PBKDF2-HMAC-SHA256 password hashing and JWT token processing module (`app/core/security.py`).
- Auth API endpoints (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`).
- Reusable FastAPI RBAC authorization dependencies (`get_current_user`, `require_roles`).
- Security rate limiting middleware (`MemoryRateLimiter`) and security exception handlers.
- Alembic database migration `001_initial_security_schema.py` for user, role, and audit tables.


### Changed
- Resolved planning-rule specifications: ROP-based criticality, Planning Availability and configurable V1 safety stock.
- Defined a mock-first SAP adapter contract for demo implementation; real SAP connectivity remains deferred.

### Fixed
- None.

### Security
- Password storage using PBKDF2-HMAC-SHA256 with salt.
- JWT authentication with signature verification and expiration handling.
- Audit trail recording for authentication attempts (success/failure) and sensitive operations.


## Release Format
For each release record:
- Added
- Changed
- Fixed
- Security
- Migration/operational notes where relevant

### Reporting / Integration Scope Update
- Added formal consolidated XLSX/CSV export requirements.
- Added controlled outbound SAP write-back requirements.
- Added authorization, idempotency, acknowledgement, retry, audit and testing requirements for these capabilities.
- Updated Claude repository guidance and README capability summary.
