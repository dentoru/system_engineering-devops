from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class TradeIn(BaseModel):
    ticket: int
    account: str
    symbol: str
    direction: str
    lots: float
    open_time: datetime
    close_time: Optional[datetime] = None
    open_price: float
    close_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    profit: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    pips: Optional[float] = None
    status: str = "open"
    comment: Optional[str] = None
    magic: Optional[int] = None
    raw_data: Optional[str] = None


class TradeOut(TradeIn):
    id: int
    synced_at: datetime

    class Config:
        from_attributes = True


class BulkTradeSync(BaseModel):
    account: str
    trades: List[TradeIn]


class JournalEntryIn(BaseModel):
    trade_ticket: Optional[int] = None
    title: Optional[str] = None
    body: str
    mood: Optional[str] = None
    tags: Optional[str] = None


class JournalEntryOut(JournalEntryIn):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncStatus(BaseModel):
    account: str
    last_sync: Optional[datetime]
    last_deal_ticket: int
