# 14 — Maintenance & Change Management

## SPIP

**Purpose:** Make SPIP maintainable months or years later without relying on an AI chat history.

## 1. Repository Is the Memory
Future developers/AI must reconstruct context from:
`CLAUDE.md → relevant docs → tracker → Git history → source/tests`.

Do not depend on Claude remembering an old conversation.

## 2. Bug Workflow
For a bug:
1. record reproduction steps;
2. capture expected vs actual result;
3. capture safe logs/request ID;
4. identify the smallest root cause;
5. add a regression test;
6. implement the smallest safe fix;
7. run relevant tests/security checks;
8. update docs if behavior changed;
9. commit through Git.

## 3. New Feature Workflow
`Requirement → Impact analysis → Update relevant spec → Feature ticket → Branch → Implement → Test → Review → Merge → Changelog`.

Do not rebuild unrelated modules.

## 4. Business Formula Changes
Never change safety stock, criticality, allocation or other planning mathematics directly in code first. Update/approve `BUSINESS_RULES.md`, add tests, then implement.

## 5. Forecast Model Changes
Compare the proposed model against the existing baseline using time-aware backtesting. Keep rollback/fallback capability.

## 6. Database Changes
All schema changes require Alembic migrations and migration testing. Never manually edit production-like schemas as the normal workflow.

## 7. Security Changes
Security controls in `SECURITY.md` cannot be weakened merely to solve an implementation problem.

## 8. Git
Use feature/fix branches and meaningful commits. Tag stable releases such as `v1.0.0`. Keep `main` stable.

## 9. Rollback
Every release must have a documented path to return to the last known stable application version. Database rollback/forward-fix strategy must be considered separately for schema/data changes.

## 10. Six-Month Claude Prompt
Use:
> Read `CLAUDE.md`, the tracker, relevant specifications and Git history. Analyze the existing implementation before changing code. Do not rebuild the application. First provide an impact/root-cause analysis, then implement only after the proposed change is understood.

## 11. Documentation
Update only documents affected by a change. Do not force Claude to reread the entire specification set for every task.
