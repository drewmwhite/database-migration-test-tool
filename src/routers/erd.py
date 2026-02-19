"""
ERD viewer routes.

GET  /erd/           — render the ERD viewer page
GET  /erd/source     — return raw Mermaid source as JSON
POST /erd/regenerate — re-introspect the DB, regenerate output/erd.md, return {ok: true}
"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from db.query import fetch_schema
from generator.mermaid import build_diagram
from src.config import settings
from src.dependencies import templates

router = APIRouter()

OUTPUT_PATH = Path(settings.output_erd_path)


def _read_diagram(path: Path) -> str | None:
    """
    Return the raw Mermaid source from the generated .md file with the
    opening ```mermaid and closing ``` fence markers stripped.
    Returns None if the file does not exist.
    """
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)


@router.get("/", response_class=HTMLResponse)
async def erd_page(request: Request):
    mermaid_source = _read_diagram(OUTPUT_PATH)
    return templates.TemplateResponse(
        "erd/index.html",
        {
            "request": request,
            "mermaid_source": mermaid_source,
            "active_page": "erd",
        },
    )


@router.get("/source")
async def erd_source():
    """Return the raw Mermaid diagram source as JSON."""
    mermaid_source = _read_diagram(OUTPUT_PATH)
    if mermaid_source is None:
        return JSONResponse({"mermaid": None}, status_code=404)
    return JSONResponse({"mermaid": mermaid_source})


@router.post("/regenerate")
async def regenerate():
    """
    Re-introspect the connected SQL Server database and rewrite output/erd.md.

    pyodbc is a blocking library, so fetch_schema is dispatched to a thread
    pool via run_in_executor to avoid stalling the async event loop.
    """
    loop = asyncio.get_event_loop()
    tables, fks = await loop.run_in_executor(None, fetch_schema)
    diagram = build_diagram(tables, fks)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(diagram + "\n", encoding="utf-8")
    return JSONResponse({"ok": True})
