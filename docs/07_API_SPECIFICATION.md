# 07 — API Specification

## SPIP

**Purpose:** Define consistent API behavior between the React frontend and FastAPI backend.

## 1. Style
Use versioned REST APIs under `/api/v1`.

Major resource groups:
- auth
- users/roles
- plants
- materials
- inventory
- consumption
- forecasts
- planning
- vendors
- allocations
- approvals
- reports
- notifications
- imports
- administration

## 2. Security
Protected endpoints require authentication and server-side authorization. Apply endpoint-specific rate limits, strict validation and safe error handling according to `SECURITY.md`.

## 3. Request/Response Contracts
Use explicit Pydantic schemas. Do not expose raw ORM/database objects. Validate path, query and body inputs.

## 4. Errors
Use a consistent safe error structure, for example:
```json
{
  "code": "ALLOCATION_EXCEEDS_AVAILABLE",
  "message": "The requested allocation cannot be completed.",
  "request_id": "..."
}
```
Never return stack traces or raw database errors.

## 5. Pagination and Filtering
Large collections must support pagination. Filtering/sorting parameters must be allowlisted and validated.

## 6. Long-Running Work
Forecast batches, large reports and bulk imports should return a job identifier instead of holding an HTTP request open until completion.

Typical flow:
`POST job → 202 Accepted → job_id → GET job status/result`.

## 7. Allocation Workflow
Allocation APIs must support:
Draft/Submit → Manager Review → Approve/Reject → Vendor Communication.

Approval permissions must be separate from ordinary planner permissions.

## 8. Concurrency
Critical write APIs must handle concurrent updates safely. Use transactions and optimistic/pessimistic controls as appropriate.

## 9. Idempotency
Use idempotency protection for operations where client retries could create duplicate critical records or communications.

## 10. File Imports
Excel/CSV upload endpoints must enforce the file-upload controls in `SECURITY.md` and return validation/import summaries.

## 11. API Documentation
FastAPI OpenAPI documentation may be available in development/staging. Production exposure must follow security policy.

## 12. Compatibility
Avoid breaking existing API contracts without versioning or an approved migration plan.

## Report Export APIs

Provide versioned APIs/jobs for authorized consolidated report generation.

Conceptual endpoints:
- `POST /api/v1/reports/exports` — request an XLSX/CSV export using validated filters.
- `GET /api/v1/jobs/{job_id}` — retrieve generation status.
- `GET /api/v1/reports/exports/{export_id}/download` — authorized download.

Exact contracts are finalized during implementation. Backend authorization and plant/data scope must be applied independently of frontend state.

## SAP Write-Back APIs / Jobs

Outbound SAP updates must be exposed only through protected application/service operations, not arbitrary client-supplied SAP payload forwarding.

Required behavior:
- validate approved business state;
- authorize the actor;
- create a traceable integration job;
- enforce idempotency;
- transmit through the SAP adapter;
- record SAP acknowledgement/reference where available;
- expose success/failure status;
- support controlled retry for transient failures;
- notify appropriate users on terminal failure.

Do not create an endpoint that allows the frontend to directly execute unrestricted SAP commands.

SAP-facing application services must use the configured adapter contract and normalized request/result structures. The API must not expose a concrete SAP transport; demo mode uses the mock adapter by default.
