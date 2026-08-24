"""
MT5 Bridge — records every trade from MetaTrader 5 into the journal backend.

Requirements (Windows only):
    pip install MetaTrader5 requests python-dotenv

Usage:
    python bridge.py

The bridge:
  1. Connects to the running MT5 terminal (logs in if credentials supplied).
  2. Polls every POLL_INTERVAL seconds for closed deals and open positions.
  3. POSTs them to the backend API's /trades/sync endpoint (upsert, idempotent).
  4. Survives restarts: on Windows install as a service via install_service.ps1.
"""

import time
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not found.\n"
          "Run:  pip install MetaTrader5\n"
          "Note: Only works on Windows with MT5 terminal installed.")
    sys.exit(1)

from config import Config


# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Bridge class ─────────────────────────────────────────────────────────────

class MT5Bridge:
    def __init__(self):
        self.api_url = Config.API_URL.rstrip("/")
        self.account_id: str = ""
        # Track the latest deal ticket already sent so we only ask MT5 for new ones
        self._last_deal_ticket: int = 0

    # ── MT5 connection ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        kwargs = {}
        if Config.MT5_PATH:
            kwargs["path"] = Config.MT5_PATH

        if not mt5.initialize(**kwargs):
            log.error("mt5.initialize() failed: %s", mt5.last_error())
            return False

        if Config.MT5_ACCOUNT:
            ok = mt5.login(Config.MT5_ACCOUNT, Config.MT5_PASSWORD, Config.MT5_SERVER)
            if not ok:
                log.error("mt5.login() failed: %s", mt5.last_error())
                return False

        info = mt5.account_info()
        if info:
            self.account_id = str(info.login)
            log.info(
                "Connected  account=%s  server=%s  balance=%.2f %s",
                info.login, info.server, info.balance, info.currency,
            )
        return True

    def _ensure_connected(self) -> bool:
        if mt5.terminal_info() is not None:
            return True
        log.warning("MT5 disconnected — reconnecting…")
        return self.connect()

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _fetch_closed_deals(self) -> list:
        if self._last_deal_ticket == 0:
            since = datetime.now() - timedelta(days=Config.HISTORY_DAYS)
        else:
            # Ask for the last hour to catch any deals we may have missed
            since = datetime.now() - timedelta(hours=1)

        to = datetime.now()
        deals = mt5.history_deals_get(since, to)
        return list(deals) if deals is not None else []

    @staticmethod
    def _direction(mt5_type: int) -> str:
        return {
            mt5.DEAL_TYPE_BUY: "buy",
            mt5.DEAL_TYPE_SELL: "sell",
        }.get(mt5_type, "balance")

    def _deal_to_dict(self, deal) -> dict:
        t = datetime.fromtimestamp(deal.time, tz=timezone.utc)
        return {
            "ticket": deal.ticket,
            "account": self.account_id,
            "symbol": deal.symbol or "",
            "direction": self._direction(deal.type),
            "lots": deal.volume,
            "open_time": t.isoformat(),
            "close_time": t.isoformat(),
            "open_price": deal.price,
            "close_price": deal.price,
            "profit": deal.profit,
            "commission": deal.commission,
            "swap": deal.swap,
            "status": "closed",
            "comment": deal.comment or "",
            "magic": deal.magic,
        }

    def _fetch_open_positions(self) -> list:
        positions = mt5.positions_get()
        if not positions:
            return []
        result = []
        for pos in positions:
            direction = "buy" if pos.type == mt5.POSITION_TYPE_BUY else "sell"
            open_t = datetime.fromtimestamp(pos.time, tz=timezone.utc).isoformat()
            result.append({
                "ticket": pos.ticket,
                "account": self.account_id,
                "symbol": pos.symbol,
                "direction": direction,
                "lots": pos.volume,
                "open_time": open_t,
                "close_time": None,
                "open_price": pos.price_open,
                "close_price": pos.price_current,
                "sl": pos.sl or None,
                "tp": pos.tp or None,
                "profit": pos.profit,
                "commission": pos.commission,
                "swap": pos.swap,
                "status": "open",
                "comment": pos.comment or "",
                "magic": pos.magic,
            })
        return result

    # ── API push ──────────────────────────────────────────────────────────────

    def _push(self, trades: list) -> bool:
        if not trades:
            return True
        payload = {"account": self.account_id, "trades": trades}
        try:
            r = requests.post(
                f"{self.api_url}/trades/sync",
                json=payload,
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            log.info("Synced %d trade(s) — %d new", data["synced"], data["new"])
            return True
        except requests.exceptions.ConnectionError:
            log.warning("API unreachable at %s — will retry next cycle", self.api_url)
        except Exception as exc:
            log.error("API push failed: %s", exc)
        return False

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        log.info("MT5 Bridge started  api=%s  poll=%ss", self.api_url, Config.POLL_INTERVAL)

        while True:
            try:
                if not self._ensure_connected():
                    time.sleep(10)
                    continue

                # ── Closed deals ──
                deals = self._fetch_closed_deals()
                # Skip pure balance/deposit entries (no symbol)
                trade_dicts = [self._deal_to_dict(d) for d in deals if d.symbol]

                # Update watermark
                if deals:
                    new_max = max(d.ticket for d in deals)
                    if new_max > self._last_deal_ticket:
                        self._last_deal_ticket = new_max

                # ── Open positions ──
                open_pos = self._fetch_open_positions()

                self._push(trade_dicts + open_pos)

            except KeyboardInterrupt:
                log.info("Bridge stopped by user (Ctrl+C)")
                break
            except Exception as exc:
                log.exception("Unexpected error in main loop: %s", exc)

            time.sleep(Config.POLL_INTERVAL)

        mt5.shutdown()
        log.info("MT5 connection closed.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bridge = MT5Bridge()
    if not bridge.connect():
        log.error("Cannot connect to MT5. Is the terminal open and logged in?")
        sys.exit(1)
    bridge.run()
