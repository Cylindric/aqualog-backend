from pydantic import ValidationError

from aqualog_api.app import create_app


try:
    app = create_app()
except ValidationError as exc:
    raise RuntimeError("Failed to start: missing/invalid mandatory configuration") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
