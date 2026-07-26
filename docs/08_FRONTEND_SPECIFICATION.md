# 08 — Frontend Specification

## SPIP

**Purpose:** Preserve the current application's familiar workflow while providing a cleaner, safer and more attractive enterprise UI.

## 1. Design Direction
Keep the existing core navigation and user workflow where it is valid. Do not redesign merely for novelty.

Visual direction:
- simple enterprise interface;
- red-and-white primary visual identity based on the reference application;
- restrained use of color;
- responsive layouts;
- clear typography and spacing.

Final exact shades should be taken from the reference UI/assets rather than guessed.

## 2. Criticality Colors
Use status color consistently:
- Critical — red
- Warning — yellow/amber
- Healthy/OK — green

Do not rely on color alone; always include a text label/icon for accessibility.

## 3. Primary Screens
Expected screens include:
- login
- dashboard
- material/inventory view
- consumption/statistics
- forecast view
- planning requirements
- vendor/allocation workflow
- manager approval queue
- reports
- notifications
- imports
- administration

## 4. Roles
Navigation and actions adapt to Admin, Planner, Procurement, Manager/Approver and Read-only roles, but backend authorization remains authoritative.

## 5. UX Requirements
Every user action must show a visible state:
- loading
- success
- validation error
- permission error
- empty state
- server/network error

Buttons must never appear to silently do nothing.

## 6. Forms
Use client-side validation for fast feedback and backend validation for authority. Display field-specific errors clearly.

## 7. Server State
Use a structured API/server-state approach such as TanStack Query for fetching, caching and invalidation.

## 8. Forecast UX
Show forecast value together with useful context such as horizon, model/fallback status and historical accuracy where available. Never imply certainty that the model cannot provide.

## 9. Allocation UX
Show:
- requirement;
- already allocated quantity;
- remaining quantity;
- current edit exclusion where relevant;
- approval status.

Manager approval/rejection must be clear and auditable.

## 10. Notifications
Provide an in-app notification area for critical material alerts, approvals, rejected actions, import failures and other approved events. Email remains a complementary channel.

## 11. Accessibility
Keyboard navigation, readable contrast, labels and non-color status indicators must be supported.

## 12. Consistency
Reusable components should be used for tables, forms, dialogs, status badges, alerts, loading states and errors.
