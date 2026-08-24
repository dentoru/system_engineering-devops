# MT5 Trading Journal

Records every trade from MetaTrader 5, stores them with a FastAPI backend,
and exposes REST endpoints for the web dashboard and journal.

---

## Quick Start

### 1. Start the backend (any OS — runs in Docker)

```bash
# From the mt5-trading-journal/ folder:
docker compose up -d
```

The API is now live at **http://localhost:8000**
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The database (`journal.db`) lives in a Docker volume — it **survives container
restarts and machine reboots automatically** because of `restart: always` in
`docker-compose.yml`.

> **No Docker?** Run manually:
> ```bash
> cd backend
> pip install -r requirements.txt
> uvicorn app.main:app --host 0.0.0.0 --port 8000
> ```

---

### 2. Configure the MT5 bridge (Windows, next to your MT5 terminal)

```bash
cd mt5_bridge
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set API_URL to http://YOUR_SERVER_IP:8000
```

**Test it manually first:**
```bash
python bridge.py
```

You should see lines like:
```
2024-01-15 09:32:01  INFO     Connected  account=12345  server=ICMarkets-Live  balance=10230.00 USD
2024-01-15 09:32:02  INFO     Synced 47 trade(s) — 47 new
```

---

### 3. Make the bridge survive reboots (Windows)

Run this **once** from an elevated PowerShell prompt:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd path\to\mt5_bridge
.\install_service.ps1
```

Then start it immediately without rebooting:
```powershell
Start-ScheduledTask -TaskName "MT5JournalBridge"
```

The bridge will now **automatically restart** after:
- Windows reboot
- MT5 terminal restarts
- Network dropouts
- Any Python crash

---

## API Reference

| Method | Endpoint | What it does |
|--------|----------|--------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/trades/sync` | Bridge posts trades here (bulk upsert) |
| `GET` | `/trades` | List trades (`?symbol=XAUUSD&status=closed`) |
| `GET` | `/trades/{ticket}` | Single trade detail |
| `POST` | `/journal` | Create journal entry |
| `GET` | `/journal` | List entries (`?trade_ticket=123`) |
| `PUT` | `/journal/{id}` | Update entry |
| `DELETE` | `/journal/{id}` | Delete entry |
| `GET` | `/analytics/summary` | Win rate, P&L, profit factor |
| `GET` | `/sync/status` | Last sync time per account |

Full interactive docs at **http://localhost:8000/docs**

---

## Project Structure

```
mt5-trading-journal/
├── backend/
│   ├── app/
│   │   ├── main.py          ← FastAPI routes
│   │   ├── models.py        ← SQLAlchemy ORM (trades, journal, sync state)
│   │   ├── schemas.py       ← Pydantic request/response models
│   │   └── database.py      ← DB engine + session factory
│   ├── requirements.txt
│   └── Dockerfile
├── mt5_bridge/
│   ├── bridge.py            ← MT5 → API sync loop (Windows)
│   ├── config.py            ← Config from .env
│   ├── .env.example         ← Copy to .env and fill in
│   ├── install_service.ps1  ← Register as Windows startup task
│   └── run.bat              ← Manual start shortcut
├── docker-compose.yml       ← Backend stack with restart: always
└── ROADMAP.md               ← Full build roadmap
```

---

## What Survives a Restart

| Component | How it survives |
|---|---|
| **Backend API** | Docker `restart: always` → container auto-restarts on crash/reboot |
| **Database** | Named Docker volume (`journal_data`) → data persists independently of container |
| **MT5 Bridge** | Windows Task Scheduler task → runs at every logon, retries on crash |
