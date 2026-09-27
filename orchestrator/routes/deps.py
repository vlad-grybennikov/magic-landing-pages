from __future__ import annotations

from typing import Optional

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from services import Services


def services(request: Request) -> Services:
    return request.app.state.services


def current_user(request: Request, authorization: Optional[str] = Header(None)) -> dict:
    return services(request).auth.authenticate(authorization)


def error(status: int, stage: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"stage": stage, "message": message, **extra}})


def not_found(stage: str, message: str) -> JSONResponse:
    return error(404, stage, message)
