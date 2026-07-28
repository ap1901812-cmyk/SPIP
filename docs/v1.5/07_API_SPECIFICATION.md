# API Specification – SPIP v1.5

## Purpose

This document defines the API additions introduced in SPIP v1.5.

Existing APIs remain unchanged unless explicitly stated.

---

# Design Principles

- RESTful APIs
- Backward Compatibility
- Consistent Response Format
- Pagination Support
- Proper Error Handling

---

# New API Modules

## Finished Goods

GET /finished-goods

GET /finished-goods/{id}

---

## Bill of Material

GET /bom

GET /bom/{fgId}

---

## Dependency

GET /materials/{id}/where-used

GET /materials/{id}/dependencies

---

## Production Risk

GET /production-risk

GET /production-risk/{fgId}

---

# Existing APIs

The following APIs remain unchanged:

- Inventory
- Forecast
- Allocation
- Reports
- Authentication

---

# Error Handling

Standard HTTP status codes shall be used.

Examples:

200 OK

400 Bad Request

401 Unauthorized

404 Not Found

500 Internal Server Error

---

# Future APIs (V2)

- Scenario Planning
- AI Recommendations
- Material Substitution