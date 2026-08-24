from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from .database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    ticket = Column(Integer, unique=True, index=True, nullable=False)
    account = Column(String(50), index=True)
    symbol = Column(String(20), index=True)
    direction = Column(String(10))          # buy / sell / balance
    lots = Column(Float)
    open_time = Column(DateTime, index=True)
    close_time = Column(DateTime, nullable=True)
    open_price = Column(Float)
    close_price = Column(Float, nullable=True)
    sl = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    profit = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    swap = Column(Float, default=0.0)
    pips = Column(Float, nullable=True)
    status = Column(String(20), default="open", index=True)  # open / closed
    comment = Column(String(255), nullable=True)
    magic = Column(Integer, nullable=True)
    raw_data = Column(Text, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    trade_ticket = Column(Integer, nullable=True, index=True)
    title = Column(String(255), nullable=True)
    body = Column(Text, default="")
    mood = Column(String(50), nullable=True)    # great / good / neutral / bad / awful
    tags = Column(String(500), nullable=True)   # comma-separated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncState(Base):
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True)
    account = Column(String(50), unique=True, index=True)
    last_sync = Column(DateTime, nullable=True)
    last_deal_ticket = Column(Integer, default=0)
