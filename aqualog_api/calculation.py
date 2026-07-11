from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from aqualog_api.auth import get_current_user
from aqualog_api.responses import success_response

GRAMS_PER_LITER_PER_PPT = 1.1  # grams per liter per ppt of salinity change


class Dose(BaseModel):
    volume: float
    current: float
    target: float
    quantity: float
    unit: str = "g"


class DoseResponse(BaseModel):
    success: bool
    request_id: str
    data: Dose

def build_calculation_router() -> APIRouter:
    router = APIRouter()

    @router.get("/calculate/dose/salinity", response_model=DoseResponse)
    async def salinity_dose(
        request: Request,
        volume: float,
        current: float,
        target: float,
        _current_user: Any = Depends(get_current_user),
    ):
        request_id = getattr(request.state, "request_id", "unknown")
        quantity = (target - current) * GRAMS_PER_LITER_PER_PPT * volume
        dose = Dose(
            volume=volume,
            current=current,
            target=target,
            quantity=quantity,
            unit="g"
        )
        return success_response(
            dose.model_dump(),
            request_id=request_id,
        )

    return router