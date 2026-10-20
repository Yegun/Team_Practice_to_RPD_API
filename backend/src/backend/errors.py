import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        fields: list[str] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or []


def error_body(code: str, message: str, fields: list[str]) -> dict:
    return {"error": {"code": code, "message": message, "fields": fields}}


def _field_path(loc: tuple) -> str:
    # ("body", "items", 0, "quantity") -> "items[0].quantity"
    parts = [p for p in loc if p != "body"]
    path = ""
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)
    return path


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=error_body(exc.code, exc.message, exc.fields),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: list[str] = []
        for err in exc.errors():
            path = _field_path(tuple(err["loc"]))
            if path and path not in fields:
                fields.append(path)
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "입력값이 올바르지 않다.", fields),
        )

    @app.exception_handler(sqlite3.Error)
    async def _storage_error(_: Request, exc: sqlite3.Error) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_body("STORAGE_ERROR", "저장소 오류.", []),
        )
