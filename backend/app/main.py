from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.schemas.errors import ErrorResponse

settings = get_settings()
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    openapi_url=settings.openapi_url,
    docs_url="/docs" if settings.openapi_url else None,
    redoc_url=None,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestContextMiddleware, settings=settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.rstrip("/") for origin in settings.allowed_origins],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["Content-Disposition"],
)



def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.code, message=exc.message, request_id=request_id_from(request)
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info("request_validation_failed", extra={"request_id": request_id_from(request)})
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="The request could not be validated.",
            request_id=request_id_from(request),
        ).model_dump(),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = (
        "The requested resource was not found." if exc.status_code == 404 else "Request failed."
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code="NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
            message=message,
            request_id=request_id_from(request),
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_application_error", extra={"request_id": request_id_from(request)})
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="Unable to complete the request.",
            request_id=request_id_from(request),
        ).model_dump(),
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)
