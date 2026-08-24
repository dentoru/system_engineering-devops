"""
MT5 Bridge configuration.
All values can be overridden via environment variables or a .env file
placed in the same directory as bridge.py.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── MT5 terminal connection ──────────────────────────────────────────────
    MT5_ACCOUNT  = int(os.getenv("MT5_ACCOUNT", "0"))     # 0 = use already-logged-in terminal
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER   = os.getenv("MT5_SERVER", "")
    MT5_PATH     = os.getenv("MT5_PATH", "")              # optional: full path to terminal64.exe

    # ── Backend API ──────────────────────────────────────────────────────────
    API_URL      = os.getenv("API_URL", "http://localhost:8000")

    # ── Sync behaviour ───────────────────────────────────────────────────────
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "15"))  # seconds between polls
    HISTORY_DAYS  = int(os.getenv("HISTORY_DAYS", "90"))   # how far back on first run

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_FILE = os.getenv("LOG_FILE", "bridge.log")
