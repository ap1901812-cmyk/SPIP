# 09 — Forecasting & ML Specification

## SPIP

**Purpose:** Define a reliable demand-forecasting framework without assuming that one ML model is best for every material.

## 1. Objective
Predict future material demand accurately enough to improve planning while remaining explainable, measurable and fault tolerant.

No model can guarantee perfect forecasts.

## 2. Available History
Initial design must work with limited history, approximately 2–6 months where that is all that exists. Therefore deep learning is not an initial requirement.

## 3. Forecasting Unit
Forecasting must be plant-aware and material-aware. Data from multiple plants must not be mixed blindly.

## 4. Baseline
Retain the current moving-average/trend approach as a baseline and fallback.

## 5. Candidate Models
Candidate families may include:
- moving average;
- exponential smoothing/ETS;
- SARIMA where sufficient seasonal history exists;
- XGBoost/LightGBM where engineered features and data volume justify them.

Do not force every model onto every material.

## 6. Features
Potential features:
- lagged consumption;
- rolling averages;
- rolling variability;
- recent trend;
- day/week/month information;
- plant/material identity;
- production-plan or calendar signals when reliable data exists.

Only use features available at prediction time; prevent data leakage.

## 7. Backtesting
Use time-aware backtesting. Never randomly shuffle time-series data for forecast evaluation.

Compare candidate models against the baseline using approved metrics such as MAE, RMSE, WMAPE and bias.

## 8. Model Selection
Select the best *validated* model per suitable material/segment, considering accuracy, stability and available data.

If history is insufficient, use an approved simpler model.

## 9. Forecast Horizon
Keep the current approximately 12-day horizon as the initial configurable baseline until business validation changes it.

## 10. Fallback
Required hierarchy:
`Selected model → approved secondary/baseline → deterministic fallback → low-confidence flag`.

Forecasting failure must not crash the planning workflow.

## 11. Uncertainty
Where practical, show a forecast range/confidence indicator and historical error rather than only a single number.

## 12. Retraining
Retraining frequency must be configurable and based on data arrival/model behavior. Do not retrain expensive models during normal interactive API requests.

## 13. Monitoring
Track:
- forecast error over time;
- bias;
- fallback frequency;
- missing/stale data;
- model/version used;
- model degradation/drift indicators.

## 14. Model Registry Metadata
For reproducibility retain model/version, training period, feature/config version, metrics and creation timestamp.

## 15. Human Oversight
Forecasts feed the deterministic planning engine. ML must not directly create purchase orders or approve allocations.

## 16. Acceptance Rule
A more complex model replaces the baseline only when backtesting demonstrates meaningful, stable improvement and operational reliability.
