# 16 — UI/UX Design Blueprint

## Supply Planning Intelligence Platform (SPIP)

**Purpose:** Define a substantially improved enterprise frontend while preserving the useful business workflow of the reference RMPM system.

> **Design intent:** The legacy RMPM frontend is a workflow reference, not a visual template. The public corporate website is branding inspiration only, not an application-layout template.

## 1. UX Goal

SPIP should feel:
- modern;
- clean;
- fast;
- professional;
- data-dense without being cluttered;
- easy for occasional as well as daily enterprise users;
- consistent across planning, allocation, approval and tracking.

Usability and clarity take priority over decorative effects.

## 2. Visual Direction

Use a light enterprise interface as the default.

Visual language:
- white / soft-neutral surfaces;
- strong but restrained red primary accent;
- dark neutral text;
- generous whitespace;
- subtle borders/shadows;
- clear hierarchy;
- large, readable KPI numbers;
- minimal visual noise.

The corporate public website may inspire the strong red/white identity, prominent numerical callouts and clean content hierarchy, but SPIP must remain an operational application rather than imitate a marketing website.

Exact brand shades/logo assets must come from approved assets or the reference source; do not invent a corporate logo.

## 3. Semantic Status Colors

Use:
- **Critical:** red
- **Warning:** amber/yellow
- **Healthy:** green
- **Informational / in-progress:** neutral or restrained blue where necessary

Never communicate status by color alone. Pair color with label/icon/text.

Brand red and critical red must be used carefully so ordinary buttons do not visually compete with genuine critical alerts.

## 4. Application Shell

Recommended desktop structure:

`Persistent sidebar → top context/header bar → page content`

Sidebar:
- Dashboard
- Planning
- Allocation
- Approvals
- Dispatch / Delivery
- History
- Master Data
- Reports
- Administration (authorized users only)

Top bar:
- current plant / plant scope;
- reporting/as-of date where relevant;
- global search where useful;
- notification center;
- user/profile menu.

The navigation may collapse on smaller screens.

## 5. Dashboard

The dashboard should answer within seconds:
1. What requires attention?
2. Which materials are at risk?
3. What changed?
4. What action should I take?

Recommended sections:
- KPI row: Total Materials, Critical, Warning, Healthy, Pending Approvals;
- critical-material priority table;
- stock/coverage/forecast summary;
- status distribution;
- top upcoming requirements;
- data freshness / last successful import;
- forecast health/fallback indicator;
- recent alerts/notifications.

KPI cards should be clickable filters/drill-downs, as in the reference system, but with clearer state and navigation.

## 6. Planning Table

The main planning table should support:
- material code + description;
- plant;
- material type;
- current stock/inventory position;
- forecast demand;
- safety stock;
- net requirement;
- coverage / lead-time context where available;
- criticality;
- reason;
- data freshness.

Features:
- search;
- plant/status/material filters;
- sorting;
- saved/clear filter state where useful;
- pagination/virtualization for large datasets;
- column visibility;
- export where authorized.

Critical rows should be easy to identify without turning the entire table red.

## 7. Material Detail

Selecting a material should open a detail page/drawer with:
- current planning position;
- criticality reason;
- consumption trend;
- forecast and uncertainty;
- safety-stock inputs;
- open/incoming POs;
- linked vendors;
- allocation history;
- audit/relevant events.

The user should be able to understand **why** the system recommends action.

## 8. Allocation Workspace

Preserve both useful reference perspectives:
- **By Material**
- **By Vendor**

Improve them into one coherent workspace.

Recommended workflow:
`Select requirement → inspect eligible vendors/POs → enter quantity/date → preview remaining balance → save draft → submit for approval`

The UI must always show:
- requirement;
- PO/open supply context;
- existing active allocations;
- remaining allocatable quantity;
- plant;
- target date;
- validation state.

Editing an allocation should clearly indicate that the current allocation is excluded from competing allocation totals.

## 9. Manager Approval

Provide a dedicated **Approvals** queue.

Manager sees:
- material;
- plant;
- vendor;
- PO;
- requested quantity;
- remaining requirement;
- target date;
- planner;
- planning/criticality context;
- comments;
- audit history.

Actions:
- Approve
- Reject with reason
- Return for changes where approved by workflow

Approval must produce immediate visible feedback and update the audit trail.

Vendor email becomes available/automatic according to approved workflow only after approval.

## 10. Vendor Communication

Use a polished communication modal/page:
- vendor;
- approved allocations;
- To/CC/BCC;
- approved template;
- optional note;
- preview;
- send state;
- retry/failure state.

Communication status should be visible in history. Avoid duplicate sends.

## 11. Dispatch / Delivery Calendar

Preserve the useful monthly calendar concept.

Improve with:
- month/week navigation where useful;
- status chips;
- per-day counts;
- plant filter;
- day detail drawer;
- search;
- clear overdue/deviation indicators.

Status terminology must match the authoritative workflow.

## 12. History & Audit UX

History should support:
- status;
- material;
- vendor;
- plant;
- date range;
- PO;
- user/action filters.

Each allocation should have a timeline:
`Created → Submitted → Approved/Rejected → Communicated → Confirmed/Received/Cancelled`

Display who performed each action and when.

## 13. Master Data

Material/vendor administration should use:
- searchable tables;
- clear create/edit forms;
- validation;
- destructive-action confirmation;
- linked-vendor management;
- lead-time/capacity parameters;
- audit visibility.

Only authorized roles see edit/delete controls.

## 14. Notifications

Add an in-app notification center for:
- newly critical materials;
- pending approvals;
- approval/rejection results;
- failed imports;
- failed forecast jobs;
- vendor communication failures;
- significant delivery deviations.

Notifications should link directly to the affected record.

## 15. Interaction Standards

Every action must have a visible state:
- loading;
- success;
- warning;
- validation failure;
- authorization failure;
- network/server failure;
- empty state.

Replace browser `alert()` calls with:
- inline validation;
- toast notifications;
- confirmation dialogs;
- persistent error panels for serious failures.

Buttons must never appear to do nothing.

## 16. Forms

Forms should:
- validate while remaining non-annoying;
- clearly mark required fields;
- preserve entered data after recoverable errors;
- disable impossible actions with explanation;
- show server validation errors near the relevant field;
- use sensible defaults without inventing business values.

## 17. Tables and Data Density

Enterprise users need dense information, but not clutter.

Use:
- sticky headers where useful;
- consistent alignment for numeric values;
- monospaced styling only where it improves codes/PO readability;
- tooltips for truncated values;
- responsive column priority;
- bulk selection only where bulk action is safe.

## 18. Forecast Visualization

Forecast UI should show:
- historical consumption;
- point forecast;
- forecast horizon;
- uncertainty/range where available;
- selected model/fallback status;
- recent accuracy metric;
- data sufficiency warning.

Do not show "AI accuracy" as a vague percentage. Use defined backtest metrics.

## 19. Multi-Plant UX

Plant context must be obvious.

Users with access to multiple plants should be able to:
- select one plant;
- select an authorized aggregate scope where allowed;
- see the active plant context on every planning/allocation screen.

Never mix plant data in a way that makes stock or allocation ambiguous.

## 20. Role-Aware UX

Frontend navigation should adapt to permissions:
- Admin: configuration/master/security administration
- Planner: planning and allocation drafts
- Procurement: vendor/PO and approved procurement-related views/actions
- Manager/Approver: approvals and oversight
- Read-only: dashboards/reports without mutations

Hiding a control is UX only; backend RBAC remains authoritative.

## 21. Responsive Design

Primary target is enterprise desktop/laptop usage, but the UI should remain usable on tablets and smaller screens.

Large planning tables may use responsive drawers/cards rather than forcing unreadable columns.

## 22. Accessibility

Minimum expectations:
- keyboard-accessible controls;
- visible focus states;
- adequate contrast;
- semantic labels;
- accessible dialogs;
- status not conveyed by color alone;
- charts accompanied by readable values/labels.

## 23. Theme

A dark mode may be retained only if it remains consistent and does not slow implementation of the primary light enterprise experience.

Light mode is the primary design target.

## 24. Component System

Build reusable components for:
- page headers;
- KPI cards;
- data tables;
- filters;
- status badges;
- forms;
- dialogs/drawers;
- toasts;
- loading skeletons;
- empty states;
- error states;
- charts;
- audit timelines.

Avoid one-off styling for every screen.

## 25. Frontend State

Use a disciplined separation:
- server state: TanStack Query or approved equivalent;
- local UI state: React state;
- authentication/identity: approved secure auth mechanism;
- forms: structured form state/validation.

Do not maintain duplicated stale copies of backend business data without a clear reason.

## 26. Performance

Frontend should:
- avoid unnecessary full-page reloads;
- paginate/virtualize large tables where necessary;
- lazy-load heavy screens when useful;
- cache server data appropriately;
- show skeleton/loading states rather than frozen UI.

## 27. Design Source Priority

When design sources conflict, use this order:

1. **Business correctness and security**
2. **SPIP Frontend Specification + this blueprint**
3. **Reference RMPM workflow**
4. **Corporate public website visual inspiration**
5. **Legacy RMPM visual styling**

The old UI must never constrain SPIP from becoming substantially better.

## 28. Claude Implementation Instruction

Claude should first reproduce the approved information architecture and workflows with reusable components, then polish visual design.

Do not:
- copy legacy JSX/CSS wholesale;
- invent a flashy dashboard disconnected from business tasks;
- overuse gradients/animations;
- expose secrets or model keys in frontend code;
- sacrifice table usability for aesthetics.

The target is a **high-quality enterprise planning application with familiar workflow and significantly improved UX**.
