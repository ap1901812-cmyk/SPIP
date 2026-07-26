# Changelog

All notable SPIP changes should be recorded here.

Use semantic versions where practical.

## [Unreleased]
### Added
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
