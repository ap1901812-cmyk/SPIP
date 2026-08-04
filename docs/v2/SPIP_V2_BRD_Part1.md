# SPIP V2 -- Business Requirements Document (BRD)

**Version:** Draft 1.0\
**Status:** In Progress\
**Project:** SPIP V2 -- Supply Planning & Inventory Platform

------------------------------------------------------------------------

# Part 1 -- Business Overview

## 1. Executive Summary

SPIP V2 is an enterprise Supply Planning & Procurement Decision Support
Platform designed to transform fragmented planning data into actionable
business recommendations. Rather than acting as a reporting application,
SPIP V2 assists planners in inventory planning, procurement planning,
production readiness assessment, and vendor allocation while preserving
the existing enterprise platform (authentication, RBAC, notifications,
reports, dashboard, multi-plant support, etc.).

The statistical planning logic adopted by SPIP V2 will reuse the
validated RMPM business logic for Lead Time, Safety Stock, Trigger
calculations, and related inventory planning without modification.

------------------------------------------------------------------------

## 2. Business Background

Most planning activities currently rely on multiple SAP reports, Excel
sheets, manual calculations, and planner experience. This leads to:

-   Fragmented planning data
-   Delayed shortage identification
-   Manual procurement decisions
-   Reactive vendor allocation
-   Limited visibility into production readiness
-   Time-consuming report preparation

SPIP V2 aims to unify these activities into a single enterprise
platform.

------------------------------------------------------------------------

## 3. Business Objectives

### Primary Objectives

-   Centralize planning data from SAP and manual sources.
-   Improve procurement planning.
-   Improve production readiness visibility.
-   Reduce manual planning effort.
-   Support proactive and reactive planning.
-   Improve decision making using enterprise dashboards and reports.

### Technical Objectives

-   Preserve existing enterprise platform.
-   Replace existing planning business logic with RMPM planning logic.
-   Add Enterprise Data Intelligence.
-   Support scalable enterprise deployment.

------------------------------------------------------------------------

## 4. Project Scope

### In Scope

-   Enterprise Data Ingestion
-   Enterprise Data Intelligence
-   Planning Readiness
-   Consumption Intelligence
-   Inventory Intelligence
-   RMPM Statistical Planning Engine
-   Forecasting
-   Requirement Resolution
-   RM Planning
-   PM Planning
-   Dependency Intelligence
-   Production Readiness
-   Proactive Planning
-   Reactive Planning
-   Procurement Recommendation
-   Dynamic Procurement Allocation
-   Dashboard
-   Reports
-   Notifications
-   Audit
-   Planning Simulation

### Out of Scope (Current Release)

-   Automatic Purchase Order creation
-   Direct ERP transaction posting
-   AI autonomous decision making

------------------------------------------------------------------------

## 5. Stakeholders

-   Planner
-   Manager
-   Administrator
-   Procurement Team
-   Vendor
-   Management
-   SAP System

------------------------------------------------------------------------

## 6. Key Design Principles

1.  Preserve the existing enterprise platform.
2.  Replace---not extend---the existing planning business logic.
3.  Reuse RMPM statistical planning logic without modification.
4.  Planner remains the final decision maker.
5.  Enterprise Data Intelligence validates and enriches data before
    planning.
6.  Every recommendation should be explainable.
7.  Multi-plant support remains available.
8.  Existing security (JWT, RBAC) remains unchanged.

------------------------------------------------------------------------

## Next Sections

The following BRD sections will continue in subsequent parts:

-   Part 2 -- Enterprise Data Layer
-   Part 3 -- Planning Intelligence
-   Part 4 -- Material Planning
-   Part 5 -- Procurement & Allocation Intelligence
-   Part 6 -- Enterprise Platform
-   Part 7 -- Non-Functional Requirements
-   Part 8 -- Future Roadmap
