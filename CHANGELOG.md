# Changelog

All notable SPIP changes should be recorded here.

Use semantic versions where practical.

## [Unreleased]
### Added
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
