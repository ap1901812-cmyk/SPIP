# Supply Planning Intelligence Platform (SPIP)

SPIP is an enterprise-grade demo supply-planning platform for RMPM planning, forecasting, material criticality, vendor allocation and approval workflows.

## Core Capabilities
- multi-plant planning
- consumption/inventory analysis
- safety stock and material criticality
- demand forecasting with validated fallback
- vendor allocation with manager approval
- SAP plus Excel/CSV ingestion
- in-app and SMTP notifications
- RBAC, auditability and enterprise security controls
- scalable FastAPI/PostgreSQL architecture

## Technology Direction
React + TypeScript frontend, FastAPI/Python backend, PostgreSQL, Docker, Git/CI, background processing and production-ready observability/security patterns.

## Development
Before changing code, read `CLAUDE.md`.

Implementation follows `11_IMPLEMENTATION_PLAN.md` and `12_FEATURE_TICKETS.md`.

## Important
This repository must not contain real credentials or sensitive enterprise data. Organization-specific names are intentionally excluded from the product documentation.

## Reporting and SAP Integration

SPIP includes:
- consolidated planning report export to **Excel (.xlsx)** and **CSV**;
- secure asynchronous generation for large exports;
- SAP/enterprise ingestion through an adapter boundary;
- controlled outbound SAP write-back for approved business actions;
- acknowledgement, retry, audit and notification handling.

The exact SAP transport/protocol remains configurable until the real enterprise integration mechanism is known.
