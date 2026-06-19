"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import create_all
from app.errors import AppError
from app.logging_config import configure_logging, get_logger

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    # For SQLite/demo we create tables directly; production uses Alembic migrations.
    if settings.DATABASE_URL.startswith("sqlite"):
        create_all()
    logger.info("startup app_env=%s", settings.APP_ENV)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Hijacking — Retail Opportunity Decision Engine",
        version="0.1.0",
        description=(
            "Automatically discovers repeated product patterns from a configured "
            "global outdoor-retail source set during the selected observation "
            "period, then determines whether each pattern is a real Swiss "
            "assortment gap."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    # Routers. The frontend-facing contract router serves the camelCase API the
    # Lovable frontend expects on /api/*. The snake_case routers
    # (source_sets/discovery_runs/opportunities/scan_items/demo) were the initial
    # internal contract and are superseded by app/api/contract.py.
    from app.api import contract, exports, health

    app.include_router(health.router)
    app.include_router(contract.router)
    app.include_router(exports.router)

    return app


app = create_app()
