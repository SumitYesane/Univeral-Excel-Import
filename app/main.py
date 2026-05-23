from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.imports import router as imports_router
from app.api.v1.routes.jobs import router as jobs_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.import_engine.services.job_tracker import JobTracker
from app.import_engine.services.profile_service import ImportProfileService
from app.utils.exceptions import ConfigurationException, ImportException


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.API_V1_PREFIX)
    app.include_router(imports_router, prefix=settings.API_V1_PREFIX)
    app.include_router(jobs_router, prefix=settings.API_V1_PREFIX)

    @app.exception_handler(ImportException)
    async def import_exception_handler(_: Request, exc: ImportException):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(ConfigurationException)
    async def configuration_exception_handler(_: Request, exc: ConfigurationException):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.on_event("startup")
    def _startup() -> None:
        JobTracker().init_db()
        ImportProfileService().seed_defaults()
        settings.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        settings.ERROR_ROOT.mkdir(parents=True, exist_ok=True)

    return app


app = create_app()
