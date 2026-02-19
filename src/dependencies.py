"""
Shared FastAPI dependencies.

Centralising the Jinja2Templates instance here lets both src/main.py and
individual routers import it without creating circular imports.
"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
