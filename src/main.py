"""
FastAPI application factory for the DB Migration Test Tool web interface.

Mounts static files, wires up routers, and defines a root redirect so that
opening http://localhost:8000 lands directly on the ERD viewer.

Usage:
    uvicorn src.main:app --reload                          # development
    uvicorn src.main:app --host 0.0.0.0 --port 8000       # production
    python run_server.py                                   # reads PORT from .env
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.routers import erd

BASE_DIR = Path(__file__).parent

app = FastAPI(title="DB Migration Test Tool")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

app.include_router(erd.router, prefix="/erd", tags=["ERD"])


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/erd")
