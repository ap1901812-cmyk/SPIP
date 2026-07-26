# 06 — Database Design

## Supply Planning Intelligence Platform (SPIP)

**Purpose:** Define the PostgreSQL data model, integrity rules, multi-plant support, migrations, and audit/history requirements.

## 1. Database
Use PostgreSQL as the durable source of truth. Redis or application memory must not store authoritative planning data.

## 2. Core Entities
Initial logical entities:
- users, roles, permissions
- plants
- materials
- plant_materials
- vendors
- vendor_materials
- consumption_history
- inventory_snapshots
- purchase_orders / incoming_supply
- forecasts
- forecast_runs / model_metadata
- planning_requirements
- allocations
- allocation_approvals
- notifications
- import_jobs
- audit_logs
- system_configuration

Exact columns are finalized during implementation from the approved API/business rules.

## 3. Multi-Plant Design
The system must support more than one plant. Plant-specific inventory, consumption, forecasting, planning and allocation records must carry an explicit plant identifier.

Do not assume that a material has identical lead time, stock, vendor availability, or planning configuration at every plant.

Material planning configuration must support ABC class, service level/Z, review period, minimum/maximum safety-stock bounds and calculation-version metadata. Availability inputs and results must retain plant, material, quantity, UOM, source and as-of timestamp for traceability.

## 4. Data Integrity
Use:
- primary and foreign keys;
- NOT NULL constraints where required;
- unique constraints;
- CHECK constraints for valid quantities/statuses;
- transactions for critical operations;
- database-level protection against invalid over-allocation where practical.

Frontend validation is not sufficient.

## 5. Quantities and Precision
Use fixed-precision numeric types for business quantities where appropriate. Units of measure must be stored explicitly and conversions must follow approved business rules.

## 6. Time
Store timestamps consistently and define the business timezone at application/configuration level. Preserve source timestamps where needed for audit and reconciliation.

## 7. History
Consumption, forecasts, allocations, approvals and important configuration changes must preserve enough history for audit and debugging. Do not overwrite historical forecast runs merely because a newer forecast exists.

## 8. Allocation Transactions
Allocation creation/editing and manager approval must be transactional. Concurrent users must not be able to create allocations that collectively exceed the approved available requirement.

## 9. Imports
SAP and Excel/CSV imports must be traceable using an import/job identifier, source type, timestamps, validation result, row counts and failure details.

## 10. Indexing
Index high-use fields such as material, plant, vendor, date, status and relevant foreign keys. Add indexes from measured query patterns rather than indexing every column.

## 11. Migrations
All schema changes use Alembic migrations. Manual production schema changes are prohibited except controlled emergency procedures.

## 12. Backup and Recovery
The production-like design must support database backup and documented restoration. A backup is not considered reliable until restoration has been tested.

## 13. Security
Use least-privilege database credentials. Secrets must not be committed to Git. Sensitive audit/security records require restricted access.

## 14. Source of Truth
`BUSINESS_RULES.md` defines calculation behavior; this document defines persistence and integrity. Detailed physical schemas may evolve through reviewed migrations.
