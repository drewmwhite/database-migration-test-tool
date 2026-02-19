"""
Production-style server entry point.

Reads HOST and PORT from .env so the server can be configured without
passing CLI flags. For development with auto-reload, prefer:

    uvicorn src.main:app --reload

For production:

    python run_server.py
    # or: uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

import uvicorn
from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
