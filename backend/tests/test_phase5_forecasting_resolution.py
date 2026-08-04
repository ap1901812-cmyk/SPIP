from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.db.models.domain import ConsumptionHistory, ForecastRecord, Material, Plant
from app.db.models.user import RoleEnum, User, UserRole
from app.services.forecasting.engine import generate_demand_forecast
from app.services.forecasting.models import MovingAverageForecastModel
from app.services.forecasting.wmape import (
    evaluate_past_forecasts_wmape,
    get_wmape_history,
    save_forecast_record,
)
from app.services.planning.requirement_resolution import resolve_planning_requirement


def _seed_planner(db: Session) -> dict[str, str]:
    user = User(
        email="planner_p5@example.com",
        full_name="Phase5 Planner",
        hashed_password=hash_password("Pass123!"),
        is_active=True,
    )
    user.roles.append(UserRole(role_name=RoleEnum.PLANNER.value))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email, roles=[RoleEnum.PLANNER.value])
    return {"Authorization": f"Bearer {token}"}


def test_extensible_moving_average_forecasting_model() -> None:
    model = MovingAverageForecastModel(window=7)
    assert model.name == "MOVING_AVERAGE_7D"
    history = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]
    predictions = model.fit_predict(history, horizon=5)
    assert len(predictions) == 5
    assert predictions[0] == 40.0  # Mean of 10..70 is 40.0


def test_wmape_lifecycle_and_backtesting(db_session: Session) -> None:
    plant = Plant(code="P-WMAPE-1", name="WMAPE Plant")
    mat = Material(code="M-WMAPE-1", description="WMAPE Material", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    target_date = date.today()

    # Step 1: Day N - Save Forecast
    f_rec = save_forecast_record(
        db=db_session,
        plant_id=plant.id,
        material_id=mat.id,
        model_name="MOVING_AVERAGE_7D",
        forecast_date=target_date,
        forecast_horizon_days=7,
        forecast_quantity=100.0,
    )
    assert f_rec.actual_consumption is None
    assert f_rec.wmape_score is None

    # Step 2: Day N+K - Record Actual Consumption
    cons = ConsumptionHistory(
        plant_id=plant.id,
        material_id=mat.id,
        consumption_date=target_date,
        quantity=120.0,
        uom="KG",
    )
    db_session.add(cons)
    db_session.commit()

    # Step 3: Evaluate WMAPE
    count = evaluate_past_forecasts_wmape(db_session)
    assert count == 1

    db_session.refresh(f_rec)
    assert f_rec.actual_consumption == 120.0
    # WMAPE = |120 - 100| / 120 * 100 = 20 / 120 * 100 = 16.67%
    assert f_rec.wmape_score == 16.67

    # Query history
    history = get_wmape_history(db_session, plant_code="P-WMAPE-1")
    assert len(history) == 1
    assert history[0]["wmape_score"] == 16.67


def test_requirement_resolution_hierarchy(db_session: Session) -> None:
    plant = Plant(code="P-REQ-1", name="Req Plant")
    mat = Material(code="M-REQ-1", description="Req Material", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    # Case 1: Priority 1 - IBP Daily
    res1 = resolve_planning_requirement(
        db_session,
        plant_id=plant.id,
        material_id=mat.id,
        forecast_daily_qty=50.0,
        historical_daily_qty=40.0,
        ibp_daily_qty=100.0,
        monthly_schedule_qty=2200.0,
    )
    assert res1.requirement_source == "IBP_DAILY"
    assert res1.final_planning_requirement == 100.0

    # Case 2: Priority 2 - Monthly Schedule
    res2 = resolve_planning_requirement(
        db_session,
        plant_id=plant.id,
        material_id=mat.id,
        forecast_daily_qty=50.0,
        historical_daily_qty=40.0,
        ibp_daily_qty=None,
        monthly_schedule_qty=2200.0,
    )
    assert res2.requirement_source == "MONTHLY_SCHEDULE"
    assert res2.final_planning_requirement == 100.0  # 2200 / 22

    # Case 3: Priority 3 - Statistical Forecast
    res3 = resolve_planning_requirement(
        db_session,
        plant_id=plant.id,
        material_id=mat.id,
        forecast_daily_qty=50.0,
        historical_daily_qty=40.0,
        ibp_daily_qty=None,
        monthly_schedule_qty=None,
    )
    assert res3.requirement_source == "STATISTICAL_FORECAST"
    assert res3.final_planning_requirement == 50.0

    # Case 4: Priority 4 - Historical Consumption
    res4 = resolve_planning_requirement(
        db_session,
        plant_id=plant.id,
        material_id=mat.id,
        forecast_daily_qty=0.0,
        historical_daily_qty=40.0,
        ibp_daily_qty=None,
        monthly_schedule_qty=None,
    )
    assert res4.requirement_source == "HISTORICAL_CONSUMPTION"
    assert res4.final_planning_requirement == 40.0


def test_forecasting_and_resolution_api_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    headers = _seed_planner(db_session)

    plant = Plant(code="P-P5-API", name="P5 API Plant")
    mat = Material(code="M-P5-API", description="P5 API Material", base_uom="KG")
    db_session.add_all([plant, mat])
    db_session.commit()

    # 1. GET /api/v1/forecasts/materials/{material_code}
    res_fc = client.get("/api/v1/forecasts/materials/M-P5-API?plant_code=P-P5-API", headers=headers)
    assert res_fc.status_code == 200
    data_fc = res_fc.json()
    assert data_fc["material_code"] == "M-P5-API"
    assert data_fc["selected_model"] is not None

    # 2. POST /api/v1/forecasts/evaluate-actuals
    res_ev = client.post("/api/v1/forecasts/evaluate-actuals", headers=headers)
    assert res_ev.status_code == 200
    assert res_ev.json()["status"] == "SUCCESS"

    # 3. GET /api/v1/forecasts/wmape-history
    res_wm = client.get("/api/v1/forecasts/wmape-history?plant_code=P-P5-API", headers=headers)
    assert res_wm.status_code == 200
    assert isinstance(res_wm.json(), list)

    # 4. GET /api/v1/planning/materials/{material_code} (Resolved requirement fields check)
    res_plan = client.get("/api/v1/planning/materials/M-P5-API?plant_code=P-P5-API", headers=headers)
    assert res_plan.status_code == 200
    data_plan = res_plan.json()
    assert "final_planning_requirement" in data_plan
    assert "requirement_source" in data_plan
