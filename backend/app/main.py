import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .db import init_db

logging.basicConfig(level=getattr(logging, get_settings().log_level.upper(), logging.INFO), format="%(message)s")
app = FastAPI(title="Autonomous Delivery Resolution Agent", version="0.1.0", description="Multi-agent delivery incident resolution API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    init_db()
