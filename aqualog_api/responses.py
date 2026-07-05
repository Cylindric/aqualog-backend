from typing import Any

from fastapi.responses import JSONResponse


def success_response(payload: Any, request_id: str, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "request_id": request_id,
            "data": payload,
        },
    )


def error_response(message: str, request_id: str, status_code: int, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "request_id": request_id,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )
