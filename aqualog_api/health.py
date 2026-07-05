from dataclasses import dataclass

from fastapi import APIRouter, Request

from aqualog_api.responses import success_response


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
        if state.is_ready:
            return success_response({"status": "ready"}, request_id=request_id)
        return success_response(
            {"status": "not_ready"},
            request_id=request_id,
            status_code=503,
        )

    return router
