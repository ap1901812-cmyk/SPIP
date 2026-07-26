from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models.domain import Material, Plant
from app.db.models.user import User
from app.schemas.forecasting import ForecastCalculationResult
from app.services.forecasting import generate_demand_forecast

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/materials/{material_code}", response_model=ForecastCalculationResult)
def get_material_demand_forecast(
    material_code: str,
    plant_code: Annotated[str, Query(description="Target plant code")],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    horizon_days: Annotated[int, Query(ge=1, le=365, description="Forecast horizon days")] = 12,
) -> ForecastCalculationResult:
    return generate_demand_forecast(
        db=db, plant_code=plant_code, material_code=material_code, horizon_days=horizon_days
    )


@router.get("/summary", response_model=list[ForecastCalculationResult])
def get_forecast_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plant_code: Annotated[str | None, Query(description="Filter by plant code")] = None,
    horizon_days: Annotated[int, Query(ge=1, le=365, description="Forecast horizon days")] = 12,
) -> list[ForecastCalculationResult]:
    query_plants = db.query(Plant)
    if plant_code:
        query_plants = query_plants.filter(Plant.code == plant_code)
    plants = query_plants.all()

    materials = db.query(Material).all()

    results: list[ForecastCalculationResult] = []
    for plant in plants:
        for mat in materials:
            try:
                res = generate_demand_forecast(
                    db=db,
                    plant_code=plant.code,
                    material_code=mat.code,
                    horizon_days=horizon_days,
                )
                results.append(res)
            except Exception:
                continue

    return results
