from __future__ import annotations

from fastapi import APIRouter, Depends

from builds import BuildNotFound
from contracts import (
    AttachRequest,
    BuildList,
    BuildPatch,
    BuildSummary,
    Deleted,
    ErrorResponse,
    OpenBuild,
)
from routes.deps import current_user, not_found, services
from services import Services
from storage import PageNotFound

router = APIRouter(prefix="/builds", tags=["builds"])

NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=BuildList)
def list_builds(user: dict = Depends(current_user), svc: Services = Depends(services)):
    return {"builds": svc.page_service.list_builds(user["id"])}


@router.post("", response_model=BuildSummary)
def create_build(user: dict = Depends(current_user), svc: Services = Depends(services)):
    return svc.builds.create(user["id"])


@router.get("/{build_id}", response_model=OpenBuild, responses=NOT_FOUND)
def get_build(build_id: str, user: dict = Depends(current_user),
              svc: Services = Depends(services)):
    try:
        return svc.page_service.open_build(build_id, user["id"])
    except BuildNotFound:
        return not_found("build", "No such build.")


@router.patch("/{build_id}", response_model=BuildSummary, responses=NOT_FOUND)
def update_build(build_id: str, patch: BuildPatch, user: dict = Depends(current_user),
                 svc: Services = Depends(services)):
    try:
        return svc.builds.update(build_id, user["id"], patch.model_dump())
    except BuildNotFound:
        return not_found("build", "No such build.")


@router.put("/{build_id}/page", response_model=BuildSummary, responses=NOT_FOUND)
def attach_page(build_id: str, req: AttachRequest, user: dict = Depends(current_user),
                svc: Services = Depends(services)):
    try:
        return svc.page_service.attach(build_id, req.page_id, user["id"])
    except PageNotFound:
        return not_found("page", "No such page.")
    except BuildNotFound:
        return not_found("build", "No such build.")


@router.delete("/{build_id}", response_model=Deleted, responses=NOT_FOUND)
def delete_build(build_id: str, user: dict = Depends(current_user),
                 svc: Services = Depends(services)):
    try:
        svc.builds.delete(build_id, user["id"])
    except BuildNotFound:
        return not_found("build", "No such build.")
    return {"deleted": build_id}
