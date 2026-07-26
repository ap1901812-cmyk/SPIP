from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.consumption import router as consumption_router
from app.api.v1.routes.forecasting import router as forecasting_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.imports import router as imports_router
from app.api.v1.routes.inventory import router as inventory_router
from app.api.v1.routes.materials import router as materials_router
from app.api.v1.routes.planning import router as planning_router
from app.api.v1.routes.plants import router as plants_router
from app.api.v1.routes.purchase_orders import router as po_router
from app.api.v1.routes.sap import router as sap_router
from app.api.v1.routes.vendors import router as vendors_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(plants_router)
api_router.include_router(materials_router)
api_router.include_router(vendors_router)
api_router.include_router(inventory_router)
api_router.include_router(consumption_router)
api_router.include_router(po_router)
api_router.include_router(imports_router)
api_router.include_router(sap_router)
api_router.include_router(planning_router)
api_router.include_router(forecasting_router)
