from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from contracts import AuthConfig, GoogleLogin, LoginResponse, RefreshRequest, TokenPair, User
from routes.deps import current_user, services
from services import Services

logger = logging.getLogger("mlp.orchestrator")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfig)
def auth_config(svc: Services = Depends(services)):
    return {"enabled": svc.auth.enabled, "mode": svc.auth.mode}


@router.post("/google", response_model=LoginResponse)
def google_login(req: GoogleLogin, svc: Services = Depends(services)):
    signed_in = svc.auth.sign_in(req.idToken)
    logger.info("/auth/google signed in %s", signed_in["user"]["email"])
    return signed_in


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(req: RefreshRequest, svc: Services = Depends(services)):
    return svc.auth.refresh(req.refreshToken)


@router.get("/me", response_model=User)
def me(user: dict = Depends(current_user)):
    return user
