import logging
from logging.config import dictConfig
from pathlib import Path
from contextlib import asynccontextmanager
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError
from starlette.staticfiles import StaticFiles

from aqualog_api.aquariums import build_aquarium_router
from aqualog_api.calculation import build_calculation_router
from aqualog_api.config import Settings, load_settings
from aqualog_api.db import init_database
from aqualog_api.health import ReadinessState, build_health_router
from aqualog_api.logging_middleware import RequestLoggingMiddleware
from aqualog_api.profile import build_profile_router
from aqualog_api.responses import error_response, success_response

# Custom JSON formatter

class JsonFormatter(logging.Formatter):

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


def configure_logging(level: str) -> logging.Logger:
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": JsonFormatter
            }
       },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level.upper(),
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": level.upper(),
                "formatter": "json",
                "filename": "fastapi.log",
                "mode": "a",
            },

        },
        "loggers": {
            "app": {"handlers": ["console"], "level": level.upper(), "propagate": False},
        },
        "root": {"handlers": ["console"], "level": level.upper()},
    }

    dictConfig(log_config)
    logger = logging.getLogger("aqualog.api")
    # if not logger.handlers:
    #     handler = logging.StreamHandler()
    #     formatter = logging.Formatter(
    #         "%(asctime)s %(name)s %(levelname)s %(message)s"
    #     )
    #     handler.setFormatter(formatter)
    #     logger.addHandler(handler)
    # logger.setLevel(level.upper())
    return logger


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    logger = configure_logging(settings.log_level)
    static_dir = Path(__file__).parent / "static"
    favicon_path = static_dir / "favicon.png"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_database(settings)
        app.state.readiness.is_ready = True
        yield

    app = FastAPI(
        title="Aqualog Backend API", 
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        redoc_url=None,
        swagger_ui_parameters={"tryItOutEnabled": True}
    )
    app.state.readiness = ReadinessState(is_ready=False)
    app.state.settings = settings
    app.state.logger = logger
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
    app.include_router(build_profile_router(), prefix=versioned_prefix)
    app.include_router(build_aquarium_router(), prefix=versioned_prefix)

    @app.get("/")
    async def root(request: Request):
        request_id = getattr(request.state, "request_id", "unknown")
        return success_response(
            {"service": "aqualog-backend-api", "version": settings.api_version},
            request_id=request_id,
        )

    @app.get("/favicon.png", include_in_schema=False)
    async def favicon_png():
        return FileResponse(favicon_path, media_type="image/png")

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
