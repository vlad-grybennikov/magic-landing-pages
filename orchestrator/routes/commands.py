from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from command_service import Execution
from contracts import CommandRecord, CommandResponse, ErrorResponse, TextCommand
from routes.deps import current_user, not_found, services
from services import Services

logger = logging.getLogger("mlp.orchestrator")

router = APIRouter(tags=["commands"])

STATUS_FOR_STAGE = {"llm": 503, "stt": 503, "conflict": 409, "cancelled": 499, "internal": 500}

STREAM = {
    200: {"content": {"text/event-stream": {
              "schema": {"$ref": "#/components/schemas/StreamEvent"}}},
          "description": "Server-sent events, one JSON object per `data:` line."},
}

REJECTED = {422: {"model": ErrorResponse}, 409: {"model": ErrorResponse},
            503: {"model": ErrorResponse}}


def _stream(events) -> StreamingResponse:
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _rejection(outcome: dict, text: str) -> JSONResponse:
    err = outcome["error"]
    status = STATUS_FOR_STAGE.get(err.get("stage"), 422)
    return JSONResponse(
        status_code=status,
        content={"recognizedCommand": text, "error": err,
                 "validation": {"valid": False}, "commandId": outcome.get("commandId")},
    )


async def _finish(svc: Services, record: dict, execution: Optional[Execution], text: str):
    if execution is not None:
        outcome = await asyncio.to_thread(svc.command_service.wait, execution)
    else:
        record = svc.commands.get(record["_id"], record["owner"]) or record
        if record["status"] == "done":
            outcome = {"type": "result", "commandId": record["_id"], "result": record["result"]}
        elif record["status"] in ("failed", "cancelled"):
            outcome = {"type": "error", "commandId": record["_id"],
                       "error": record.get("error") or {"stage": record["status"],
                                                        "message": record["status"]}}
        else:
            return JSONResponse(status_code=202, content={
                "commandId": record["_id"], "status": record["status"],
                "message": "Still running -- fetch /commands/{id} for the result."})
    if outcome["type"] == "result":
        return {**outcome["result"], "commandId": outcome["commandId"]}
    return _rejection(outcome, text)


@router.post("/command", response_model=CommandResponse, responses=REJECTED)
async def execute_command(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    page_id: Optional[str] = Form(None),
    build_id: Optional[str] = Form(None),
    answering: bool = Form(False),
    section: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    idempotency_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
    svc: Services = Depends(services),
):
    audio = await file.read()
    ctx = svc.command_service.context(user, session_id, page_id, answering, section, model)
    record, execution = svc.command_service.submit(
        user["id"], build_id, "", svc.command_service.audio_run(audio, ctx),
        idempotency_key or idempotency_header)
    return await _finish(svc, record, execution, "")


@router.post("/command/text", response_model=CommandResponse, responses=REJECTED)
async def execute_text_command(
    req: TextCommand,
    idempotency_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
    svc: Services = Depends(services),
):
    logger.info("/command/text: %r", req.text)
    ctx = svc.command_service.context(user, req.session_id, req.page_id, req.answering,
                                      req.section, req.model)
    record, execution = svc.command_service.submit(
        user["id"], req.build_id, req.text, svc.command_service.text_run(req.text, ctx),
        req.idempotency_key or idempotency_header)
    return await _finish(svc, record, execution, req.text)


@router.post("/command/text/stream", responses=STREAM)
async def stream_text_command(
    req: TextCommand,
    idempotency_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
    svc: Services = Depends(services),
):
    logger.info("/command/text/stream: %r", req.text)
    ctx = svc.command_service.context(user, req.session_id, req.page_id, req.answering,
                                      req.section, req.model)
    record, execution = svc.command_service.submit(
        user["id"], req.build_id, req.text, svc.command_service.text_run(req.text, ctx),
        req.idempotency_key or idempotency_header)
    return _stream(svc.command_service.events(record["_id"], user["id"], execution))


@router.post("/command/stream", responses=STREAM)
async def stream_command(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    page_id: Optional[str] = Form(None),
    build_id: Optional[str] = Form(None),
    answering: bool = Form(False),
    section: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    idempotency_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    user: dict = Depends(current_user),
    svc: Services = Depends(services),
):
    audio = await file.read()
    ctx = svc.command_service.context(user, session_id, page_id, answering, section, model)
    record, execution = svc.command_service.submit(
        user["id"], build_id, "", svc.command_service.audio_run(audio, ctx),
        idempotency_key or idempotency_header)
    return _stream(svc.command_service.events(record["_id"], user["id"], execution))


@router.get("/commands/{command_id}", response_model=CommandRecord,
            responses={404: {"model": ErrorResponse}})
def command_status(command_id: str, user: dict = Depends(current_user),
                   svc: Services = Depends(services)):
    record = svc.command_service.status(command_id, user["id"])
    if record is None:
        return not_found("command", "No such command.")
    return record


@router.get("/commands/{command_id}/events", responses=STREAM)
async def command_events(command_id: str, user: dict = Depends(current_user),
                         svc: Services = Depends(services)):
    return _stream(svc.command_service.events(command_id, user["id"]))


@router.delete("/commands/{command_id}", response_model=CommandRecord,
               responses={404: {"model": ErrorResponse}})
def cancel_command(command_id: str, user: dict = Depends(current_user),
                   svc: Services = Depends(services)):
    record = svc.command_service.cancel(command_id, user["id"])
    if record is None:
        return not_found("command", "No such command.")
    return svc.commands.view(record)
