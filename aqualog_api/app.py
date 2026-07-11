import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.staticfiles import StaticFiles

from aqualog_api.calculation import build_calculation_router
from aqualog_api.config import Settings, load_settings
from aqualog_api.health import ReadinessState, build_health_router
from aqualog_api.logging_middleware import RequestLoggingMiddleware
from aqualog_api.responses import error_response, success_response


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("aqualog.api")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logger = configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup dependency checks would run here in real environments.
        app.state.readiness.is_ready = True
        yield

    app = FastAPI(title="Aqualog Backend API", lifespan=lifespan, swagger_ui_parameters={"tryItOutEnabled": True})
    app.state.readiness = ReadinessState(is_ready=False)
    app.state.settings = settings
    app.state.logger = logger

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware, logger=logger)

    if settings.app_env in {"dev", "test"}:
        test_report_dir = Path(settings.test_reports_dir)
        test_report_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/tests", StaticFiles(directory=test_report_dir, html=True), name="tests")

        coverage_report_dir = Path(settings.coverage_reports_dir)
        coverage_report_dir.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/coverage",
            StaticFiles(directory=coverage_report_dir, html=True),
            name="coverage",
        )

    versioned_prefix = f"/api/{settings.api_version}"
    app.include_router(build_health_router(app.state.readiness), prefix=versioned_prefix)
    app.include_router(build_calculation_router(), prefix=versioned_prefix)

    @app.get("/")
    async def root(request: Request):
        request_id = getattr(request.state, "request_id", "unknown")
        return success_response(
            {"service": "aqualog-backend-api", "version": settings.api_version},
            request_id=request_id,
        )

    @app.exception_handler(ValidationError)
    async def settings_validation_exception_handler(request: Request, _exc: ValidationError):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            message="Invalid request payload.",
            request_id=request_id,
            status_code=422,
            code="validation_error",
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        _exc: RequestValidationError,
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            message="Invalid request payload.",
            request_id=request_id,
            status_code=422,
            code="validation_error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, _exc: Exception):
        request_id = getattr(request.state, "request_id", "unknown")
        return error_response(
            message="An internal server error occurred.",
            request_id=request_id,
            status_code=500,
            code="internal_error",
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions including authentication failures (401)."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.warning(
            f"HTTP {exc.status_code} error: {exc.detail}",
            extra={"request_id": request_id},
        )
        return error_response(
            message=exc.detail or "Request failed",
            request_id=request_id,
            status_code=exc.status_code,
            code="authentication_error" if exc.status_code == 401 else "http_error",
        )

    return app
