from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

from contracts import StreamEvent
from llm import ModelUnknown
from routes import auth as auth_routes
from routes import builds as build_routes
from routes import commands as command_routes
from routes import media as media_routes
from routes import pages as page_routes
from routes import system as system_routes
from services import Services
from settings import Settings

logger = logging.getLogger("mlp.orchestrator")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [orchestrator] %(message)s", "%H:%M:%S"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def create_app(settings: Optional[Settings] = None,
               services: Optional[Services] = None,
               warm: bool = True) -> FastAPI:
    settings = (settings or Settings.from_env()).validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = services or Services.from_settings(settings)
        app.state.services.ensure_indexes()
        if warm and services is None:
            app.state.services.providers.warm()
            app.state.services.transcriber.load()
        logger.info("orchestrator up (%s mode, auth %s)", settings.env,
                    "on" if settings.auth_enabled else "off")
        try:
            yield
        finally:
            app.state.services.close()

    app = FastAPI(title="Magic Landing Pages", version="2.0.0", lifespan=lifespan)
    app.state.settings = settings
    if services is not None:
        app.state.services = services

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ModelUnknown)
    async def unknown_model(request: Request, exc: ModelUnknown):
        return JSONResponse(
            status_code=422,
            content={"error": {"stage": "model", "message": str(exc)}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logger.exception("unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"stage": "internal", "message": "Internal server error."}},
        )

    for router in (system_routes.router, auth_routes.router, build_routes.router,
                   command_routes.router, page_routes.router, media_routes.router):
        app.include_router(router)

    def openapi() -> dict:
        if app.openapi_schema is None:
            app.openapi_schema = get_openapi(
                title=app.title, version=app.version, routes=app.routes)
            schemas = app.openapi_schema.setdefault("components", {}).setdefault("schemas", {})
            events = TypeAdapter(StreamEvent).json_schema(
                ref_template="#/components/schemas/{model}")
            schemas.update(events.pop("$defs", {}))
            schemas["StreamEvent"] = events
        return app.openapi_schema

    app.openapi = openapi
    return app
