from __future__ import annotations

from fastapi import APIRouter, Depends

from contracts import IconList, ImageList
from routes.deps import current_user, services
from services import Services

router = APIRouter(tags=["media"])


@router.get("/images", response_model=ImageList)
def search_images(q: str = "", k: int = 12, user: dict = Depends(current_user),
                  svc: Services = Depends(services)):
    limit = max(1, min(k, 36))
    query = (q or "").strip()
    if not query:
        return {"images": []}
    return {"images": svc.providers.images.rank(query, limit)}


@router.get("/icons", response_model=IconList)
def search_icons(q: str = "", k: int = 40, user: dict = Depends(current_user),
                 svc: Services = Depends(services)):
    return {"icons": svc.providers.icons.rank((q or "").strip(), max(1, min(k, 400)))}
