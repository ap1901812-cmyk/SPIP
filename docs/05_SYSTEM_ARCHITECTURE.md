# 05 — System Architecture
Supply Planning Intelligence Platform (SPIP)
Purpose: Define the high-level architecture, component responsibilities, data flow, scalability, and
deployment structure of SPIP .
### 1. High-Level Architecture
                    USERS
                      ↓
               Web Application
              React + TypeScript
                      ↓
                  HTTPS/API
                      ↓
                LOAD BALANCER
                /     |
               ↓      ↓       ↓
           FastAPI  FastAPI  FastAPI
           Instance Instance Instance
                \     |      /
                 \    |     /
                  ↓   ↓   ↓
              BUSINESS LAYER
          ┌─────────┼─────────┐
          ↓         ↓         ↓
      Planning   Allocation  Reporting
       Engine      Engine
          │
          ↓
     Forecasting Engine
          │
          ↓
     Background Jobs
          │
     ┌────┴───────────┐
     ↓                ↓
 PostgreSQL          Redis
     ↑
     │
Enterprise Data / SAP
The architecture shall remain modular without introducing unnecessary microservices.

### 2. Frontend Layer
Technology: React + TypeScript
Responsibilities:
dashboards;
material views;
forecasts;
allocations;
reports;
administration;
user interaction.
The frontend communicates with the backend through secured APIs.
The frontend shall never directly access PostgreSQL.
React
  ↓
FastAPI
  ↓
PostgreSQL
### 3. Load Balancer
Production architecture shall support a load-balancing layer .
Instead of every request going to one backend:
Users
  ↓
Load Balancer
  ↓
Available FastAPI Instance
Benefits:
distributes traffic;
supports horizontal scaling;
improves availability;
allows multiple backend instances;
reduces dependence on one application server .
If one backend instance becomes unavailable, healthy instances should continue serving requests
where infrastructure permits.
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

Exact load-balancing technology will depend on deployment environment.
### 4. FastAPI Application Layer
FastAPI handles:
APIs;
authentication integration;
authorization;
validation;
business-service coordination;
database access;
background-job submission.
FastAPI routes should remain thin.
Example:
API Request
    ↓
Validation
    ↓
Authorization
    ↓
Service Layer
    ↓
Business Logic
    ↓
Database
Mathematical formulas shall not be duplicated across different API routes.
### 5. Business Layer
Core domain logic shall be separated into modules such as:
Business Services
│
├── Material
├── Inventory
├── Consumption
├── Planning
├── Criticality
├── Allocation
├── Vendor
•
•
•
•
•
•
•

├── Reporting
└── Notification
This separation makes individual modules easier to test and modify.
### 6. Forecasting Engine
Forecasting shall be logically separated from normal API processing.
Historical Data
      ↓
Forecasting Engine
      ↓
Data Preparation
      ↓
Candidate Models
      ↓
Backtesting
      ↓
Selected Model
      ↓
Forecast
      ↓
PostgreSQL
The API should consume validated forecast outputs rather than retraining complex models during
normal user requests.
Detailed behavior belongs in the Forecasting & ML Specification.
### 7. Background Processing
Long-running operations shall execute asynchronously where appropriate.
Examples:
forecasting batches;
model training;
report generation;
bulk data import;
notifications.
Flow:
•
•
•
•
•

User/API
   ↓
Create Job
   ↓
Background Queue
   ↓
Worker
   ↓
Process
   ↓
Save Result
The user can receive job status rather than keeping one HTTP request open for several minutes.
### 8. PostgreSQL
PostgreSQL is the primary durable application datastore.
It stores data such as:
materials;
consumption;
inventory;
purchase-order information where applicable;
vendors;
allocations;
forecasts;
configuration;
audit information.
Critical business data must not depend solely on Redis or application memory.
### 9. Redis
Redis may support:
distributed rate limiting;
caching;
background-job coordination;
short-lived state.
Concept:
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

FastAPI #1 ─┐
FastAPI #2 ─┼→ Redis
FastAPI #3 ─┘
This is important when multiple FastAPI instances exist.
For example, authentication rate limiting must work across all instances, not separately on each server .
Redis is not the authoritative database for planning data.
### 10. Enterprise/SAP Integration
SPIP may receive planning information from SAP or other approved enterprise systems.
Concept:
SAP / Enterprise Source
          ↓
      Integration
          ↓
      Validation
          ↓
     PostgreSQL
          ↓
        SPIP
Invalid source data shall not silently enter critical calculations.
The integration mechanism may use approved APIs, files, scheduled imports, or another enterprise
integration method.
### 11. Security Architecture
Every protected request follows:
Request
   ↓
Rate Limit
   ↓
Authentication
   ↓
Authorization
   ↓
Input Validation

↓
Business Logic
   ↓
Database
Security requirements are governed by 03_SECURITY_AND_ACCESS_CONTROL.md.
### 12. Planning Data Flow
A typical planning cycle is:
SAP / Source Data
       ↓
Validation
       ↓
Consumption + Inventory + PO
       ↓
Consumption Statistics
       ↓
Demand Forecast
       ↓
Safety Stock
       ↓
Net Requirement
       ↓
Criticality
       ↓
Planner Dashboard
       ↓
Allocation
       ↓
Approval / Communication
       ↓
Audit History
This is the core business flow of SPIP .
### 13. Scalability
SPIP shall primarily scale using horizontal application scaling.
Instead of:
One extremely large server

the architecture can support:
FastAPI 1
FastAPI 2
FastAPI 3
...
behind a load balancer .
Additional instances can be introduced when actual demand requires them.
### 14. Stateless Backend
FastAPI instances should remain stateless wherever practical.
Do not depend on:
Server #1 memory
for information required by future requests.
Shared persistent/distributed information belongs in appropriate services such as:
PostgreSQL;
Redis;
approved object/file storage.
This allows any healthy backend instance to handle the next request.
### 15. High Availability
Production architecture should avoid unnecessary single points of failure.
Conceptually:
                Load Balancer
               /
          Backend A       Backend B
               \            /
                PostgreSQL
More advanced database redundancy, backup, failover and disaster-recovery architecture shall depend
on actual enterprise infrastructure requirements.
•
•
•

### 16. Docker Deployment
Application components shall support containerized deployment.
Example:
Docker
│
├── Frontend
├── Backend
├── Worker
└── Supporting Services
Development may use Docker Compose.
Production deployment architecture will depend on the selected hosting environment.
### 17. Observability
All major components shall support monitoring.
Monitor:
backend health;
API latency;
error rates;
database health;
background jobs;
forecasting failures;
integration failures;
authentication/security events.
Requests should use correlation IDs to simplify debugging across components.
### 18. Failure Handling
Individual component failures should degrade gracefully where possible.
Example:
ML Model Failure
       ↓
Fallback Forecast
       ↓
Planning continues
•
•
•
•
•
•
•
•

↓
Warning logged
Similarly, notification failure should not undo an already valid allocation transaction.
### 19. Architecture Simplicity
SPIP shall not initially require:
microservices;
Kubernetes;
Kafka;
service mesh;
distributed databases.
These may be introduced later only when measurable scale or operational requirements justify them.
Initial architecture:
Modular monolith + separated forecasting/background processing + scalable
infrastructure
This provides enterprise engineering quality without unnecessary distributed-system complexity.
### 20. Architecture Summary
React / TypeScript
        ↓
Load Balancer
        ↓
FastAPI Instances
        ↓
Business Services
   ↙         ↓         ↘
Forecast   Redis    Background Jobs
   \         |         /
          PostgreSQL
              ↑
        SAP / Enterprise Data
This architecture provides:
security;
scalability;
load balancing;
maintainability;
•
•
•
•
•
•
•
•
•

forecasting capability;
background processing;
centralized data integrity;
future extensibility.
Source of Truth: This document defines the high-level SPIP system architecture. Detailed database, API,
frontend and forecasting designs are defined in their respective specifications.
End of System Architecture
•
•
•
•

## Bidirectional SAP Integration and Report Export

```text
SAP / Excel / CSV
        ↓
 Ingestion Adapters
        ↓
 Validation / Normalization
        ↓
 PostgreSQL → Planning / Forecasting
        ↓
 Approved Business Action
        ↓
 Manager Approval (where required)
        ↓
 SAP Outbound Adapter
        ↓
 SAP Acknowledgement
        ↓
 Status + Audit + Notification
```

SAP integration is bidirectional at the architecture boundary, but the exact transport/protocol remains configurable until the real enterprise interface is known.

Report export flow:

```text
Authorized User → Filtered Report Request → Report Service
                                      ↓
                         Background Job if large
                                      ↓
                           XLSX / CSV Artifact
                                      ↓
                         Authorized Download
```
