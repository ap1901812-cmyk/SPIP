# 04 — Technical Requirements Document (TRD)
Supply Planning Intelligence Platform (SPIP)
Purpose: Define the technical foundation, technology stack, engineering standards, and major
implementation requirements for SPIP .
### 1. Technical Architecture
SPIP shall use a modern web architecture:
React + TypeScript Frontend
            ↓
        REST APIs
            ↓
     FastAPI Backend
            ↓
 ┌──────────┼───────────┐
 ↓          ↓           ↓
Business  Forecasting  Background
Logic      Engine        Jobs
 ↓          ↓           ↓
 └──────────┼───────────┘
            ↓
       PostgreSQL
Supporting infrastructure will provide caching, rate limiting, monitoring, load balancing, security, and
asynchronous processing.
### 2. Core Technology Stack
Layer Technology
Frontend React + TypeScript
Build Tool Vite
Backend Python + FastAPI
API REST + OpenAPI
ORM SQLAlchemy 2.x
Validation Pydantic
Database PostgreSQL

Layer Technology
DB MigrationsAlembic
ML/Data Python ecosystem
Testing Pytest + frontend testing tools
Version ControlGit
Containers Docker
The existing FastAPI + React + PostgreSQL foundation is retained because it is fully capable of
supporting an enterprise application when implemented correctly.
A complete technology rewrite is unnecessary.
### 3. Frontend
Use:
React + TypeScript + Vite
TypeScript shall be used strictly enough to catch common data-contract errors during development.
The frontend shall have clear separation between:
Pages
↓
Components
↓
Application/API state
↓
API client
↓
Backend
Recommended server-state management:
TanStack Query
It will handle API-related concerns such as:
fetching;
caching;
retries where safe;
loading states;
invalidation;
refetching.
•
•
•
•
•
•

Final UI component/design-system choices belong in the Frontend Specification.
### 4. Backend
Use:
Python + FastAPI
Backend responsibilities include:
authentication integration;
authorization;
validation;
business logic;
inventory calculations;
allocations;
forecasting orchestration;
reporting;
integrations;
audit events.
Suggested logical structure:
API Routes
    ↓
Service / Application Layer
    ↓
Domain / Business Logic
    ↓
Repository / Data Access
    ↓
PostgreSQL
Critical mathematical logic must not be scattered directly across API route handlers.
### 5. Database
Use:
PostgreSQL
PostgreSQL will store authoritative application data including:
users/roles where applicable;
materials;
•
•
•
•
•
•
•
•
•
•
•
•

planning data;
consumption history;
inventory information;
allocations;
forecast metadata/results;
configuration;
audit-related records.
Schema changes shall use:
Alembic migrations
Production database schemas must never depend on developers manually modifying tables.
### 6. Caching & Rate-Limit Infrastructure
A distributed in-memory store such as Redis is recommended where justified.
Potential uses:
distributed rate limiting;
safe caching;
short-lived application state;
background-job infrastructure.
Redis shall not become the authoritative store for critical planning data.
PostgreSQL remains the durable source of truth.
### 7. Background Processing
Long-running operations shall not unnecessarily execute inside normal HTTP requests.
Examples:
forecast generation;
model retraining;
large reports;
bulk imports;
notification delivery;
scheduled processing.
Conceptually:
API
 ↓
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Job Queue
 ↓
Worker
 ↓
Long-running operation
The final worker/job technology will be selected during architecture implementation based on actual
workload requirements rather than added solely for complexity.
### 8. Forecasting & ML
Forecasting shall be implemented as a clearly separated Python module/service boundary.
Potential model families may include:
Moving Average baseline;
Exponential Smoothing / ETS;
SARIMA where suitable;
gradient-boosted models such as XGBoost or LightGBM where justified.
The system shall not assume one model is best for every material.
Model selection must depend on historical backtesting.
Concept:
Material History
      ↓
Feature/Data Preparation
      ↓
Candidate Models
      ↓
Backtesting
      ↓
Best Valid Model
      ↓
Forecast
Detailed implementation belongs in 09_FORECASTING_AND_ML.md.
Deep learning shall only be introduced if data volume and measured performance justify the additional
complexity.
•
•
•
•

### 9. Authentication & Authorization
The backend shall implement the requirements defined in 03_SECURITY_AND_ACCESS_CONTROL.md.
The final authentication design must support:
secure identity verification;
RBAC;
session/token expiry;
revocation;
administrative security;
MFA integration where required.
Exact authentication libraries and identity-provider integration shall be selected based on deployment
environment.
Security shall not depend on frontend route protection.
### 10. API Design
SPIP shall expose versioned APIs.
Example:
/api/v1/materials
/api/v1/forecasts
/api/v1/allocations
API requirements include:
explicit schemas;
consistent responses;
standardized errors;
pagination;
authorization;
validation;
OpenAPI documentation;
appropriate idempotency for critical operations.
Detailed contracts belong in 07_API_SPECIFICATION.md.
### 11. Load Balancing & Horizontal Scaling
The backend shall be designed to support multiple application instances.
•
•
•
•
•
•
•
•
•
•
•
•
•
•

Concept:
             Load Balancer
            /      |
           ↓       ↓       ↓
       FastAPI  FastAPI  FastAPI
       Instance Instance Instance
            \      |      /
             Shared Services
                  ↓
             PostgreSQL
Application servers should remain stateless wherever practical.
Session/rate-limit state that must work across instances shall use appropriate shared infrastructure.
The exact load-balancer technology shall be selected in the System Architecture document.
### 12. Containerization
Use Docker to provide reproducible environments.
Major deployable components may include:
Frontend
Backend
Worker
Supporting Infrastructure
Secrets shall never be embedded inside container images.
### 13. Environments
Support separate:
Development
Testing
Staging
Production
Each environment shall have independent configuration and credentials.
Production secrets must never be reused casually in development.
•
•
•
•

### 14. CI/CD
Git-based development shall use an automated pipeline.
Concept:
Code Change
    ↓
Lint / Static Checks
    ↓
Automated Tests
    ↓
Security Scans
    ↓
Build
    ↓
Approved Deployment
A failed critical test or security quality gate shall block release.
Exact CI/CD platform will depend on the chosen Git hosting/deployment environment.
### 15. Testing Stack
Backend:
Pytest
integration tests
database tests
Frontend:
Vitest
React Testing Library
end-to-end testing framework selected during implementation
Forecasting:
mathematical validation;
backtesting;
regression tests.
Critical workflows shall have automated integration/E2E coverage.
•
•
•
•
•
•
•
•
•

### 16. Logging & Observability
Production systems shall use structured logging rather than scattered print() statements.
Important requests should support correlation/request IDs.
Monitor:
API errors;
latency;
failed jobs;
database health;
integrations;
forecasting failures;
authentication/security events.
Exact monitoring platform shall remain deployment-dependent.
### 17. Configuration
Environment-dependent values shall be external configuration.
Examples:
Database connection
Allowed origins
Rate limits
Authentication settings
Service URLs
Forecast configuration
Logging configuration
Secrets must follow SECURITY.md.
Hardcoded environment-specific configuration is prohibited.
### 18. Engineering Quality
Implementation shall use:
type hints;
modular code;
consistent naming;
linting/formatting;
•
•
•
•
•
•
•
•
•
•
•

dependency pinning/locking;
automated tests;
code review;
documented APIs;
Git version control.
Duplicated large modules like those discovered in the reference application shall not be retained.
### 19. Repository Structure
Target conceptual structure:
SPIP/
│
├── backend/
├── frontend/
├── forecasting/
├── tests/
├── infrastructure/
│
├── docs/
│   ├── core/
│   ├── specifications/
│   └── delivery/
│
├── CLAUDE.md
├── CHANGELOG.md
└── README.md
The final internal folder structure will be defined during implementation.
### 20. Technology Decision Summary
Keep
Python
FastAPI
PostgreSQL
React
TypeScript
Add / Upgrade
SQLAlchemy 2.x
Pydantic
Alembic
•
•
•
•
•
•
•
•
•
•
•
•
•

TanStack Query
Docker
Git
automated testing
CI/CD
structured logging/monitoring
distributed rate limiting
background processing
enterprise forecasting framework
load-balancing capability
Do Not Add Without Evidence
Microservices
Kubernetes
Deep learning
Kafka
unnecessary distributed databases
These technologies may be useful at larger scale, but SPIP shall not introduce infrastructure complexity
without a measurable requirement.
### 21. Source-of-Truth Hierarchy
This TRD defines how SPIP should technically be built at a high level.
Use:
PRD.md → product requirements
BUSINESS_RULES.md → mathematical/business logic
SECURITY.md → security requirements
TRD.md → technology decisions
ARCHITECTURE.md → how technical components connect
specialized specifications → implementation details
Claude shall read only the documents relevant to its current feature ticket.
End of Technical Requirements Document
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
•
