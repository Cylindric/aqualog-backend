from dataclasses import dataclass

from fastapi import APIRouter, Request

from src.responses import success_response


@dataclass
class ReadinessState:
    is_ready: bool = False


def build_health_router(state: ReadinessState) -> APIRouter:
    router = APIRouter()

    @router.get("/live")
    async def liveness(request: Request):
        request_id = getattr(request.state, "request_id", "unknown")
        return success_response({"status": "healthy"}, request_id=request_id)

    @router.get("/ready")
    async def readiness(request: Request):
        request_id = getattr(request.state, "request_id", "unknown")

        status = {}
        for key, value in request.app.state.settings.model_dump().items():
            if type(value) in {str, int, float, bool}:
                status[key] = value
        status["status"] = "ready" if state.is_ready else "not_ready"

        if state.is_ready:
            return success_response(status, request_id=request_id)
        return success_response(
            status,
            request_id=request_id,
            status_code=503,
        )

    return router
