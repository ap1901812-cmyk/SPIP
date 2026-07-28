# Database Design – SPIP v1.5

## Purpose

This document defines the database enhancements required for SPIP v1.5 while preserving compatibility with the existing schema.

---

# Design Strategy

SPIP v1.5 extends the current database instead of redesigning it.

Goals:

- Preserve existing tables.
- Minimize migration effort.
- Support future scalability.

---

# Material Classification

Every material shall be classified as one of:

- Finished Good (FG)
- Raw Material (RM)
- Packaging Material (PM)

Recommended field:

material_type

Allowed values:

- FG
- RM
- PM

---

# Bill of Material (BOM)

A new BOM entity shall define the relationship between Finished Goods and their components.

Suggested fields:

- id
- fg_material_id
- component_material_id
- required_quantity
- unit_of_measure
- effective_from
- effective_to
- is_active

---

# Relationships

Finished Good

↓

BOM

↓

Raw Material

Packaging Material

---

# Forecast Ownership

Forecast records belong only to Finished Goods.

RM and PM demand shall be derived during planning.

---

# Database Migration

Migration shall:

- Preserve existing data.
- Avoid destructive changes.
- Use Alembic.
- Support rollback.

---

# Future Scope (V2)

- BOM Versioning
- Material Substitution
- Multi-Plant Support
- Supplier Mapping