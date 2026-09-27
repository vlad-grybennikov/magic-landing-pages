from __future__ import annotations

from fastapi import APIRouter, Depends

from contracts import Health, ModelList, Ready
from routes.deps import current_user, services
from services import Services

router = APIRouter(tags=["system"])


@router.get("/health", response_model=Health)
def health(svc: Services = Depends(services)):
    return {"status": "ok", "release": svc.settings.release, "commit": svc.settings.commit}


@router.get("/ready", response_model=Ready)
def ready(svc: Services = Depends(services)):
    mongo = svc.ping()
    providers = svc.providers.loaded()
    transcriber = svc.transcriber.loaded
    return {
        "status": "ready" if mongo and all(providers.values()) and transcriber else "degraded",
        "mongo": mongo,
        "providers": providers,
        "transcriber": transcriber,
        "commands": svc.command_service.live(),
    }


@router.get("/models", response_model=ModelList)
def models(user: dict = Depends(current_user), svc: Services = Depends(services)):
    return {"models": svc.providers.models.describe()}
