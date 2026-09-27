from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from contracts import (
    CommandResponse,
    EditRequest,
    ErrorResponse,
    OpenPage,
    PublicPage,
    PublishRequest,
    PublishResponse,
    RenameRequest,
    RenameResponse,
    RestoreRequest,
    RestoreResponse,
    UnpublishRequest,
    UnpublishResponse,
    VersionSnapshot,
)
from pipeline import PipelineError, StaleRevision
from readiness import NotReady
from routes.deps import current_user, error, not_found, services
from schema import summarize_errors
from services import Services
from storage import PageNotFound, RevisionConflict, UrlTaken, VersionNotFound

logger = logging.getLogger("mlp.orchestrator")

router = APIRouter(tags=["pages"])

NOT_FOUND = {404: {"model": ErrorResponse}}
CONFLICT = {409: {"model": ErrorResponse}}
REJECTED = {422: {"model": ErrorResponse}}


def _conflict(e) -> object:
    return error(409, "conflict",
                 f"The page has changed since you loaded it (you have v{e.expected}, "
                 f"it is at v{e.current}) -- refresh to see the latest version.",
                 expected=e.expected, current=e.current)


@router.post("/edit", response_model=CommandResponse,
             responses={**NOT_FOUND, **CONFLICT, **REJECTED})
def edit(req: EditRequest, user: dict = Depends(current_user),
         svc: Services = Depends(services)):
    batch = ([{"action": c.action, "args": c.args} for c in req.changes]
             if req.changes is not None
             else [{"action": req.action, "args": req.args}])
    try:
        return svc.page_service.edit(req.page_id, user["id"], batch,
                                     req.expected_version, svc.providers)
    except StaleRevision as e:
        return _conflict(e)
    except PipelineError as e:
        logger.warning("/edit rejected at %s gate: %s", e.stage, e.message)
        return error(422, e.stage, e.message)


@router.get("/pages/{page_id}", response_model=OpenPage, responses=NOT_FOUND)
def open_page(page_id: str, user: dict = Depends(current_user),
              svc: Services = Depends(services)):
    try:
        return svc.page_service.open(page_id, user["id"])
    except PageNotFound:
        return not_found("page", "No such page.")


@router.post("/pages/url", response_model=RenameResponse,
             responses={**NOT_FOUND, **CONFLICT})
def rename_page(req: RenameRequest, user: dict = Depends(current_user),
                svc: Services = Depends(services)):
    try:
        moved = svc.page_service.rename(req.page_id, user["id"], req.wanted)
    except PageNotFound:
        return not_found("page", "No such page.")
    except UrlTaken as e:
        return error(409, "publish", f"{e} is taken by another page.")
    logger.info("/pages/url %s -> %s", req.page_id, moved["url"])
    return moved


@router.get("/versions/{version}", response_model=VersionSnapshot, responses=NOT_FOUND)
def version_snapshot(version: int, page_id: str, user: dict = Depends(current_user),
                     svc: Services = Depends(services)):
    try:
        return svc.page_service.version(page_id, user["id"], version)
    except PageNotFound:
        return not_found("page", "No such page.")
    except VersionNotFound:
        return not_found("publish", f"That page has no version {version}.")


@router.post("/versions/restore", response_model=RestoreResponse,
             responses={**NOT_FOUND, **CONFLICT})
def restore(req: RestoreRequest, user: dict = Depends(current_user),
            svc: Services = Depends(services)):
    try:
        restored = svc.page_service.restore(req.page_id, user["id"], req.version,
                                            req.expected_version)
    except PageNotFound:
        return not_found("page", "No such page.")
    except VersionNotFound:
        return not_found("publish", f"That page has no version {req.version}.")
    except RevisionConflict as e:
        return _conflict(e)
    logger.info("/versions/restore %s <- v%d", req.page_id, req.version)
    return restored


@router.post("/publish", response_model=PublishResponse,
             responses={**NOT_FOUND, **REJECTED})
def publish(req: PublishRequest, user: dict = Depends(current_user),
            svc: Services = Depends(services)):
    try:
        published = svc.page_service.publish(req.page_id, user["id"], req.version)
    except PageNotFound:
        return not_found("page", "No such page.")
    except VersionNotFound:
        return not_found("publish", f"That page has no version {req.version}.")
    except NotReady as e:
        logger.warning("/publish refused by readiness policy: %s",
                       e.readiness["blocking"] + e.readiness["warnings"])
        return error(422, "readiness", str(e), readiness=e.readiness)
    except ValidationError as e:
        message = summarize_errors(e)
        logger.warning("/publish rejected at schema gate: %s", message)
        return error(422, "schema", message)
    logger.info("/publish published %s v%d", req.page_id, published["version"])
    return published


@router.post("/unpublish", response_model=UnpublishResponse, responses=NOT_FOUND)
def unpublish(req: UnpublishRequest, user: dict = Depends(current_user),
              svc: Services = Depends(services)):
    try:
        return svc.page_service.unpublish(req.page_id, user["id"])
    except PageNotFound:
        return not_found("page", "No such page.")


@router.get("/public", response_model=PublicPage, responses=NOT_FOUND)
def public_page(url: str, svc: Services = Depends(services)):
    page = svc.page_service.public(url)
    if page is None:
        return not_found("page", f"Nothing is published at {url}.")
    return page
