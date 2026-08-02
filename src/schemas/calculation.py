from __future__ import annotations

from pydantic import BaseModel


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
