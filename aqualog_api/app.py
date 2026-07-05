import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

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

    app = FastAPI(title="Aqualog Backend API", lifespan=lifespan)
    app.state.readiness = ReadinessState(is_ready=False)
    app.state.settings = settings
    app.state.logger = logger

    app.add_middleware(RequestLoggingMiddleware, logger=logger)

    versioned_prefix = f"/api/{settings.api_version}"
    app.include_router(build_health_router(app.state.readiness), prefix=versioned_prefix)

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

    return app
