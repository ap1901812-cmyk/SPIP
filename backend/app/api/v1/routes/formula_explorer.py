from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.user import RoleEnum, User
from app.services.admin.formula_explorer import (
    AdminFormulaExplorerRegistry,
    FormulaExplorerEntry,
)

router = APIRouter(prefix="/admin/formulas", tags=["admin-formula-explorer"])

admin_only_role = require_roles(RoleEnum.ADMIN.value)


@router.get(
    "",
    response_model=list[FormulaExplorerEntry],
    summary="List All Formula Explorer Entries",
    description="Read-only catalog allowing administrators to inspect every business formula and planning rule in SPIP V2 (Admin only).",
)
def api_list_admin_formulas(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only_role),
) -> list[FormulaExplorerEntry]:
    return AdminFormulaExplorerRegistry.list_formulas()


@router.get(
    "/{formula_id}",
    response_model=FormulaExplorerEntry,
    summary="Get Formula Detail",
    description="Retrieves mathematical formula, inputs, outputs, and description for a specific rule (Admin only).",
)
def api_get_admin_formula_detail(
    formula_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only_role),
) -> FormulaExplorerEntry:
    return AdminFormulaExplorerRegistry.get_formula_by_id(formula_id=formula_id)
