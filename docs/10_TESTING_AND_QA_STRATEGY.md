# 10 — Testing & QA Strategy

## SPIP

**Purpose:** Ensure generated and future-modified code remains correct, secure and maintainable.

## 1. Test Layers
Use:
- unit tests;
- business-rule/math tests;
- API/integration tests;
- database tests;
- frontend component tests;
- end-to-end tests;
- security tests;
- forecasting backtests;
- performance/load tests for critical paths.

## 2. Highest-Priority Tests
Protect:
- authentication/RBAC;
- safety stock and planning formulas;
- criticality;
- allocation/edit logic;
- manager approval;
- concurrency/over-allocation;
- imports;
- forecasting fallback;
- vendor communication status.
- ROP-based Planning Availability and Critical/Warning/Healthy boundaries, including no-double-subtraction cases.
- safety-stock class defaults, configurable rolling windows and lead-time fallback/data-quality flags.

## 3. Regression Rule
Every reproducible bug fix should add a regression test.

## 4. Security QA
Automate where practical:
- dependency audit;
- secret scan;
- input-validation tests;
- authorization tests;
- rate-limit tests;
- upload-security tests.

## 5. Forecast QA
Use time-aware backtesting and compare models with the approved baseline. Prevent leakage between training and evaluation periods.

## 6. E2E Critical Flow
At minimum test:
`Login → View planning data → Create allocation → Submit → Manager approve/reject → Notification/email workflow`.

## 7. Performance
Test representative concurrent users, dashboard/API latency, forecast jobs, imports and allocation concurrency. Load-balancer behavior should be verified in a production-like environment.

## 8. CI Quality Gate
A merge/release must be blocked when critical tests or mandatory security checks fail.

## 9. Test Data
Use synthetic/anonymized test data. Do not place real sensitive enterprise data in the repository.

## 10. Definition of Done
A feature is not Done until its acceptance criteria pass, relevant tests pass, security requirements are satisfied and required documentation/tracker entries are updated.

## Export and SAP Write-Back Tests

Test consolidated exports for:
- XLSX and CSV generation;
- correct filter/scope application;
- RBAC and plant-level access control;
- expected columns/data types;
- empty and large datasets;
- background-job success/failure;
- secure download authorization.

Test SAP write-back for:
- authorization;
- strict payload validation;
- required approval state;
- idempotency/duplicate prevention;
- successful acknowledgement/reference capture;
- transient retry behavior;
- permanent failure handling and notifications;
- audit events;
- confirmation that forecast/ML output cannot directly trigger an unauthorized write.
- mock-adapter contract compatibility so a real adapter can replace it without changing planning logic.
