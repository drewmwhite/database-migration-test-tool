"""
Centralised settings for the web server.

Reads from the project .env file using the same find_dotenv / load_dotenv
pattern used by db/query.py. Exposes a single frozen Settings instance so
the .env file is parsed exactly once per process.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

# Project root is one level up from this file (src/)
_PROJECT_ROOT = Path(__file__).parent.parent


@dataclass(frozen=True)
class Settings:
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")
    output_erd_path: Path = _PROJECT_ROOT / "output" / "erd.md"


settings = Settings()
