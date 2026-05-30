# MT5 Trading Journal — Full Roadmap

## Overview

A Windows desktop app + web dashboard that connects to MetaTrader 5, automatically syncs trades, and lets traders journal each trade with notes, screenshots, tags, and emotional state — then visualizes everything in a web dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  MetaTrader 5 Terminal (Windows)                            │
│  ├── Expert Advisor (MQL5) — pushes trade events via HTTP   │
│  └── MT5 Python bridge — polls history & live positions     │
└────────────────────┬────────────────────────────────────────┘
                     │ trades / events
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend API  (Python / FastAPI)                            │
│  ├── /trades     — CRUD for synced trades                   │
│  ├── /journal    — journal entries (notes, tags, images)    │
│  ├── /analytics  — stats, drawdown, win-rate, R:R           │
│  └── /auth       — JWT authentication                       │
│                                                             │
│  PostgreSQL  ←→  Redis (cache / task queue)                 │
│  Celery worker   — scheduled MT5 sync, report generation    │
└────────────────────┬────────────────────────────────────────┘
                     │ REST / WebSocket
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐   ┌──────────────────────────────────────┐
│  Windows Desktop │   │  Web Dashboard  (React + Vite)       │
│  App (PyQt6 or   │   │  ├── Trade list & detail view        │
│  Electron)       │   │  ├── Journal editor (rich text)      │
│  ├── System tray │   │  ├── Analytics charts (Recharts)     │
│  ├── Live P&L    │   │  ├── Calendar heatmap                │
│  ├── Quick-note  │   │  └── Export (PDF / CSV)              │
│  └── Screenshot  │   └──────────────────────────────────────┘
│    capture       │
└──────────────────┘
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| MT5 bridge | `MetaTrader5` Python lib | Official, no MQL5 needed for polling |
| Backend | FastAPI + Uvicorn | Async, fast, auto OpenAPI docs |
| Task queue | Celery + Redis | Scheduled sync, async jobs |
| Database | PostgreSQL + SQLAlchemy | Relational, good for analytics queries |
| Migrations | Alembic | Schema versioning |
| Desktop app | PyQt6 (Windows) | Native look, bundles with PyInstaller |
| Web frontend | React + Vite + TypeScript | Fast dev, rich ecosystem |
| Charts | Recharts + TradingView Lightweight Charts | Free, embeddable |
| Auth | JWT (python-jose) + bcrypt | Stateless, simple |
| Containerization | Docker Compose (backend + db + redis) | One-command dev setup |

---

## Phase 1 — MT5 Data Bridge (Week 1–2)

Goal: reliably pull trade data from MT5 into a local database.

### 1.1 MT5 Python Connection Module
- [ ] Install & configure `MetaTrader5` package
- [ ] `mt5_client.py`: connect / reconnect logic with error handling
- [ ] Pull closed deals from `history_deals_get()` with date ranges
- [ ] Pull open positions from `positions_get()`
- [ ] Pull account info (balance, equity, margin)
- [ ] Map raw MT5 structs → internal `Trade` dataclass

### 1.2 Trade Normalisation
- [ ] Map MT5 deal types (buy/sell, in/out, balance entries) to clean enums
- [ ] Calculate derived fields: pips gained, R-multiple, duration, commission + swap
- [ ] Handle partial close sequences — group deals into a single `TradeRecord`

### 1.3 Sync Engine (Celery task)
- [ ] `sync_trades.py`: periodic task, runs every 60 s (or on MT5 event)
- [ ] Upsert logic — skip already-synced deals, update still-open positions
- [ ] Sync state table: last synced timestamp per account

**Deliverable:** CLI script `python sync.py --account 12345` that dumps trade history to DB.

---

## Phase 2 — Database & API (Week 2–3)

### 2.1 Database Schema

```
accounts         — MT5 account number, broker, currency, owner
trades           — ticket, symbol, direction, open/close time, lots, prices, pnl, fees
journal_entries  — trade_id (nullable), body (markdown), mood, tags[], images[]
tags             — name, color, category (setup / mistake / market)
screenshots      — trade_id, file_path, captured_at, caption
daily_summaries  — date, gross_pnl, net_pnl, trade_count, win_count, notes
users            — email, hashed_password, settings (JSON)
```

### 2.2 FastAPI Endpoints

```
POST   /auth/register
POST   /auth/login          → JWT
GET    /auth/me

GET    /trades              ?from=&to=&symbol=&tag=&page=&limit=
GET    /trades/{id}
PATCH  /trades/{id}         — add tags, set setup name

GET    /journal
POST   /journal             — create entry (linked to trade or standalone)
PUT    /journal/{id}
DELETE /journal/{id}

POST   /screenshots         — upload image, link to trade
DELETE /screenshots/{id}

GET    /analytics/summary   — win rate, avg R, profit factor, max DD
GET    /analytics/calendar  — daily P&L heatmap data
GET    /analytics/symbols   — per-symbol breakdown
GET    /analytics/sessions  — London / NY / Asian P&L split
GET    /analytics/streaks   — win/loss streak table

GET    /export/csv
GET    /export/pdf
```

### 2.3 Background Jobs
- [ ] `sync_task`: pull MT5 every minute while terminal is open
- [ ] `daily_summary_task`: runs at midnight, writes `daily_summaries` row
- [ ] `cleanup_task`: purge orphaned screenshot files

**Deliverable:** Swagger UI at `localhost:8000/docs` with all endpoints working.

---

## Phase 3 — Windows Desktop App (Week 3–4)

Goal: lightweight system-tray companion that sits next to MT5.

### 3.1 Core Window (PyQt6)
- [ ] Main window: live positions table with real-time P&L (polls API every 5 s)
- [ ] Trade closed event → popup: "EURUSD closed +$42. Add note?"
- [ ] Quick-journal modal: mood picker, tag selector, free-text note, screenshot button
- [ ] System tray icon: shows daily P&L, right-click menu

### 3.2 Screenshot Capture
- [ ] Hotkey (e.g. `Ctrl+Shift+J`) triggers region-capture overlay
- [ ] Auto-links screenshot to last-closed trade
- [ ] Uploads to backend, shows thumbnail in quick-journal modal

### 3.3 Settings Panel
- [ ] MT5 path / login / password / server fields
- [ ] API endpoint (for when running backend remotely)
- [ ] Notification preferences

### 3.4 Build & Distribution
- [ ] Bundle with PyInstaller → single `.exe`
- [ ] NSIS installer script
- [ ] Auto-update check on startup (compare version vs. backend `/version` endpoint)

**Deliverable:** Installable `.exe` that syncs trades and lets traders add notes without leaving their trading workflow.

---

## Phase 4 — Web Dashboard (Week 4–6)

### 4.1 Project Setup
- [ ] Vite + React + TypeScript scaffold
- [ ] Tailwind CSS + shadcn/ui component library
- [ ] React Query for API data fetching
- [ ] React Router for navigation
- [ ] Zustand for auth/session state

### 4.2 Pages & Components

**Dashboard (Home)**
- Account summary bar: balance, equity, daily P&L, win rate
- Equity curve chart (TradingView Lightweight Charts)
- Daily P&L calendar heatmap
- Recent trades widget

**Trade List**
- Filterable, sortable table
- Columns: time, symbol, direction, lots, entry, exit, pips, P&L, R, tags
- Row click → Trade Detail

**Trade Detail**
- Entry / exit prices, duration, fees breakdown
- Linked journal entries (rich-text viewer/editor)
- Screenshots carousel
- Add tag / setup name inline

**Journal**
- Standalone journal (not trade-linked) — daily reflection
- Calendar sidebar to navigate by date
- Markdown editor (react-markdown + CodeMirror)

**Analytics**
- Win rate / profit factor / avg R per symbol, per session, per tag
- Drawdown chart
- Trade duration histogram
- Best / worst setups ranked

**Settings**
- Account management (connect multiple MT5 accounts)
- Tag editor, risk parameters (default R value per lot size)

### 4.3 Real-time Updates
- [ ] WebSocket connection for live open positions P&L
- [ ] Toast notification when a new trade syncs

### 4.4 Export
- [ ] CSV export of filtered trade list
- [ ] PDF report: monthly summary with equity curve, stats table, top setups

**Deliverable:** Full web dashboard accessible at `localhost:5173` (dev) or hosted URL.

---

## Phase 5 — Deployment & Hardening (Week 6–7)

### 5.1 Docker Compose Stack
```yaml
services:
  api:       # FastAPI + Uvicorn
  worker:    # Celery worker (trade sync)
  beat:      # Celery beat (scheduler)
  db:        # PostgreSQL 16
  redis:     # Redis 7
  frontend:  # Nginx serving built React app
```

### 5.2 Cloud Hosting Options
- **Self-hosted VPS** (Hetzner/DigitalOcean): cheapest, full control — recommended
- **Railway / Render**: zero-ops, free tier available for low traffic
- MT5 bridge still runs on local Windows machine, pushes to cloud API

### 5.3 Security
- [ ] HTTPS via Let's Encrypt (Caddy reverse proxy)
- [ ] Rate limiting on auth endpoints
- [ ] Image upload validation (type + size limits)
- [ ] Secrets via `.env` / Docker secrets (never in code)
- [ ] MT5 credentials stored locally only, never sent to API

### 5.4 Monitoring
- [ ] Sentry for API error tracking
- [ ] Uptime check (BetterUptime or UptimeRobot)
- [ ] Celery Flower for task monitoring

---

## Phase 6 — Advanced Features (Week 8+)

| Feature | Description |
|---|---|
| Multi-account | Switch between live / demo / multiple brokers |
| Replay mode | Step through a trade bar-by-bar using stored OHLC data |
| AI trade feedback | Send journal + trade stats to Claude API for pattern insights |
| Risk calculator | Position size widget integrated in desktop app |
| Broker comparison | Same strategy across accounts — which fills are better? |
| Mobile PWA | Progressive Web App wrapper for the dashboard |
| Webhooks | Notify Telegram / Discord on trade close |

---

## Repository Structure

```
mt5-trading-journal/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # config, security, db session
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # business logic
│   │   │   ├── mt5_client.py
│   │   │   ├── sync_service.py
│   │   │   └── analytics_service.py
│   │   └── tasks/        # Celery tasks
│   ├── alembic/          # DB migrations
│   ├── tests/
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/          # React Query hooks
│   │   └── stores/       # Zustand stores
│   ├── public/
│   └── Dockerfile
├── desktop/
│   ├── main.py           # PyQt6 entry point
│   ├── widgets/
│   ├── mt5_bridge.py
│   └── build.spec        # PyInstaller spec
├── docker-compose.yml
├── docker-compose.prod.yml
└── ROADMAP.md
```

---

## Suggested Build Order (MVP in 4 weeks)

```
Week 1:  MT5 bridge + DB schema + basic sync (Phase 1 + 2.1)
Week 2:  FastAPI with /trades + /journal + /analytics (Phase 2.2–2.3)
Week 3:  React dashboard — trade list, detail, basic charts (Phase 4.1–4.2)
Week 4:  Desktop quick-journal app + screenshot capture (Phase 3)
Week 5+: Polish, auth, deployment, advanced analytics
```

---

## Quick Start (once code exists)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # fill in MT5 credentials + DB URL
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Desktop (Windows)
cd desktop
pip install -r requirements.txt
python main.py
```
