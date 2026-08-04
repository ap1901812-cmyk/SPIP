# SPIP V2 -- Technical Design Document (TDD)

## 1. Purpose

Define the technical implementation strategy for SPIP V2 while
preserving the existing SPIP enterprise platform.

## 2. Existing Platform Components (Preserved)

-   Authentication (JWT)
-   RBAC
-   Admin Panel
-   User Management
-   Notifications
-   Manager Queue
-   Reports
-   Dashboard
-   Multi-Plant Support
-   Docker Deployment
-   SAP Connectivity

## 3. Components to Replace

-   Existing Planning Logic
-   Existing Forecasting Logic
-   Existing Procurement Logic
-   Existing Material Planning Logic

These will be replaced with the RMPM statistical planning logic and the
new SPIP V2 planning workflow.

## 4. New Components

-   Enterprise Data Intelligence Engine
-   Auto Master Generation
-   Planning Readiness Engine
-   Requirement Resolution Engine
-   RM Planning Engine
-   PM Planning Engine
-   Dependency Intelligence Engine
-   Production Readiness Engine
-   Proactive Planning Engine
-   Reactive Planning Engine
-   Procurement Recommendation Engine
-   Dynamic Procurement Allocation Engine
-   Explainability Engine
-   Planning Simulation Engine

## 5. High-Level Module Flow

Enterprise Data → Data Ingestion → Enterprise Data Intelligence →
Planning Readiness → RMPM Statistical Planning → Forecasting →
Requirement Resolution → RM/PM Planning → Dependency Intelligence →
Production Readiness → Planning → Proactive/Reactive Planning →
Procurement Recommendation → Allocation → Dashboard / Reports /
Notifications

## 6. Migration Strategy

-   Preserve platform modules.
-   Replace planning business logic.
-   Reuse UI where possible.
-   Maintain API compatibility whenever feasible.
-   Validate after each migrated module.

## 7. Deliverables

-   Updated Backend
-   Updated Frontend
-   Updated Database
-   Updated APIs
-   Regression Tested Application
