"""FastAPI application factory (web edge entry point).

Run locally (requires the web deps from requirements.txt on a supported Python):
    uvicorn app.main:app --reload

The factory builds the service container once and attaches it to app state.
Set R2 credentials in the environment to serve real synthesis; without them the
app still starts (dev mode) and reports clips as not-yet-available.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .api.routes import router
from .core.container import build_container


def create_app() -> FastAPI:
    # Strict R2 validation only when explicitly requested for real serving.
    require_r2 = os.environ.get("REQUIRE_R2", "false").lower() == "true"
    container = build_container(require_r2=require_r2)

    app = FastAPI(
        title="IMO-ISHORA Backend",
        version=__version__,
        description="Uzbek text to Russian Sign Language video synthesis (MVP).",
    )
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()

__all__ = ["app", "create_app"]
