from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from . import models, schemas
from .database import engine, get_db

# ── Auto-create tables on startup (no migration tool needed for SQLite dev) ──
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MT5 Trading Journal API",
    version="1.0.0",
    description="Records trades from MetaTrader 5 and stores journal entries.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────
#  Trade sync (called by MT5 bridge)
# ─────────────────────────────────────────────

@app.post("/trades/sync", summary="Bulk upsert trades from the MT5 bridge")
def sync_trades(payload: schemas.BulkTradeSync, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    new_count = 0

    for trade in payload.trades:
        existing = (
            db.query(models.Trade)
            .filter(models.Trade.ticket == trade.ticket)
            .first()
        )
        data = trade.dict()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.synced_at = now
        else:
            db.add(models.Trade(**data, synced_at=now))
            new_count += 1

    # Track last sync time per account
    state = (
        db.query(models.SyncState)
        .filter(models.SyncState.account == payload.account)
        .first()
    )
    if not state:
        state = models.SyncState(account=payload.account)
        db.add(state)
    state.last_sync = now
    if payload.trades:
        state.last_deal_ticket = max(t.ticket for t in payload.trades)

    db.commit()
    return {"synced": len(payload.trades), "new": new_count}


# ─────────────────────────────────────────────
#  Trade read endpoints
# ─────────────────────────────────────────────

@app.get("/trades", response_model=List[schemas.TradeOut])
def list_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    account: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(models.Trade)
    if symbol:
        q = q.filter(models.Trade.symbol == symbol)
    if status:
        q = q.filter(models.Trade.status == status)
    if account:
        q = q.filter(models.Trade.account == account)
    return q.order_by(models.Trade.open_time.desc()).offset(offset).limit(limit).all()


@app.get("/trades/{ticket}", response_model=schemas.TradeOut)
def get_trade(ticket: int, db: Session = Depends(get_db)):
    t = db.query(models.Trade).filter(models.Trade.ticket == ticket).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trade not found")
    return t


# ─────────────────────────────────────────────
#  Journal
# ─────────────────────────────────────────────

@app.post("/journal", response_model=schemas.JournalEntryOut)
def create_entry(entry: schemas.JournalEntryIn, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    obj = models.JournalEntry(**entry.dict(), created_at=now, updated_at=now)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/journal", response_model=List[schemas.JournalEntryOut])
def list_entries(
    trade_ticket: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.JournalEntry)
    if trade_ticket is not None:
        q = q.filter(models.JournalEntry.trade_ticket == trade_ticket)
    return q.order_by(models.JournalEntry.created_at.desc()).all()


@app.put("/journal/{entry_id}", response_model=schemas.JournalEntryOut)
def update_entry(
    entry_id: int, entry: schemas.JournalEntryIn, db: Session = Depends(get_db)
):
    obj = db.query(models.JournalEntry).filter(models.JournalEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry not found")
    for k, v in entry.dict().items():
        setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@app.delete("/journal/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    obj = db.query(models.JournalEntry).filter(models.JournalEntry.id == entry_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(obj)
    db.commit()
    return {"deleted": entry_id}


# ─────────────────────────────────────────────
#  Analytics
# ─────────────────────────────────────────────

@app.get("/analytics/summary")
def analytics_summary(account: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Trade).filter(models.Trade.status == "closed")
    if account:
        q = q.filter(models.Trade.account == account)
    trades = q.all()

    if not trades:
        return {"total_trades": 0}

    winners = [t for t in trades if (t.profit or 0) > 0]
    losers = [t for t in trades if (t.profit or 0) < 0]
    gross_profit = sum(t.profit for t in winners)
    gross_loss = abs(sum(t.profit for t in losers)) or 1
    net_pnl = sum((t.profit or 0) + (t.commission or 0) + (t.swap or 0) for t in trades)

    return {
        "total_trades": len(trades),
        "win_rate": round(len(winners) / len(trades) * 100, 1),
        "net_pnl": round(net_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "avg_win": round(gross_profit / len(winners), 2) if winners else 0,
        "avg_loss": round(gross_loss / len(losers), 2) if losers else 0,
        "best_trade": max((t.profit or 0) for t in trades),
        "worst_trade": min((t.profit or 0) for t in trades),
    }


# ─────────────────────────────────────────────
#  Sync state (bridge heartbeat check)
# ─────────────────────────────────────────────

@app.get("/sync/status", response_model=List[schemas.SyncStatus])
def sync_status(db: Session = Depends(get_db)):
    return db.query(models.SyncState).all()
