# Testing & QA Strategy – SPIP v1.5

## Purpose

This document defines the testing approach for SPIP v1.5.

---

# Objectives

- Preserve existing functionality.
- Validate new features.
- Prevent regressions.
- Ensure production readiness.

---

# Testing Levels

## Unit Testing

Validate:

- Planning calculations
- BOM logic
- Dependency calculations

---

## API Testing

Verify:

- Existing APIs
- New APIs
- Authentication
- Error handling

---

## Integration Testing

Validate integration between:

- Forecast
- Planning
- Inventory
- Allocation
- Dashboard

---

## UI Testing

Verify:

- Navigation
- FG Workspace
- Dependency View
- Dashboard

---

## Regression Testing

Existing SPIP functionality must continue to operate without changes.

---

# Acceptance Criteria

A release is approved only when:

- All tests pass
- No critical bugs remain
- Documentation is updated