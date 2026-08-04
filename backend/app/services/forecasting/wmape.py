from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.domain import ConsumptionHistory, ForecastRecord, Material, Plant


def save_forecast_record(
    db: Session,
    plant_id: int,
    material_id: int,
    model_name: str,
    forecast_date: date,
    forecast_horizon_days: int,
    forecast_quantity: float,
    confidence_score: float = 1.0,
    details_json: str | None = None,
) -> ForecastRecord:
    """Save initial forecast record prior to actual consumption occurrence."""
    rec = ForecastRecord(
        plant_id=plant_id,
        material_id=material_id,
        model_name=model_name,
        forecast_date=forecast_date,
        forecast_horizon_days=forecast_horizon_days,
        forecast_quantity=forecast_quantity,
        confidence_score=confidence_score,
        details_json=details_json,
    )
    db.add(rec)
    try:
        db.commit()
        db.refresh(rec)
    except Exception:
        db.rollback()
    return rec


def evaluate_past_forecasts_wmape(db: Session) -> int:
    """Scan stored forecast records where actual consumption has not yet been recorded.

    When actual consumption becomes available, calculate WMAPE without future-data leakage.
    """
    today = date.today()
    pending_recs = (
        db.query(ForecastRecord)
        .filter(
            ForecastRecord.actual_consumption.is_(None),
            ForecastRecord.forecast_date <= today,
        )
        .all()
    )

    evaluated_count = 0
    for rec in pending_recs:
        # Query actual consumption for forecast date
        cons = (
            db.query(ConsumptionHistory)
            .filter(
                ConsumptionHistory.plant_id == rec.plant_id,
                ConsumptionHistory.material_id == rec.material_id,
                ConsumptionHistory.consumption_date == rec.forecast_date,
            )
            .first()
        )
        if cons:
            actual_qty = float(cons.quantity)
            rec.actual_consumption = actual_qty

            abs_err = abs(actual_qty - rec.forecast_quantity)
            wmape = (abs_err / actual_qty * 100.0) if actual_qty > 0 else (abs_err * 100.0)
            rec.wmape_score = round(wmape, 2)
            evaluated_count += 1

    if evaluated_count > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()

    return evaluated_count


def get_wmape_history(
    db: Session,
    plant_code: str | None = None,
    material_code: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve WMAPE model performance history."""
    query = db.query(ForecastRecord).filter(ForecastRecord.wmape_score.isnot(None))

    if plant_code:
        plant = db.query(Plant).filter(Plant.code == plant_code).first()
        if plant:
            query = query.filter(ForecastRecord.plant_id == plant.id)

    if material_code:
        mat = db.query(Material).filter(Material.code == material_code).first()
        if mat:
            query = query.filter(ForecastRecord.material_id == mat.id)

    records = query.order_by(ForecastRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "id": rec.id,
            "plant_code": rec.plant.code if rec.plant else None,
            "material_code": rec.material.code if rec.material else None,
            "model_name": rec.model_name,
            "forecast_date": rec.forecast_date.isoformat(),
            "forecast_quantity": rec.forecast_quantity,
            "actual_consumption": rec.actual_consumption,
            "wmape_score": rec.wmape_score,
            "confidence_score": rec.confidence_score,
            "created_at": rec.created_at.isoformat(),
        }
        for rec in records
    ]
