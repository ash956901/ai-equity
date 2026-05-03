"""Quote / candle / peer API routes (ticker-keyed, broker-app feel)."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.domains.auth.dependencies import optional_user
from src.domains.quotes.service import QuotesDomainService

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/{ticker}")
def get_quote(
    ticker: str,
    db: Session = Depends(get_db),
    _user=Depends(optional_user),
) -> dict[str, Any]:
    """Live LTP + day range + change% for a ticker. Public; auth optional."""
    return QuotesDomainService(db).get_quote(ticker)


@router.get("/{ticker}/candles")
def get_candles(
    ticker: str,
    range: str = Query("1Y", alias="range"),
    interval: Optional[str] = None,
    db: Session = Depends(get_db),
    _user=Depends(optional_user),
) -> dict[str, Any]:
    """Historical OHLCV. range one of: 1D | 1W | 1M | 6M | 1Y | 5Y | MAX."""
    return QuotesDomainService(db).get_candles(
        ticker=ticker, rng=range, interval=interval
    )


@router.get("/{ticker}/peers")
def get_peers(
    ticker: str,
    limit: int = Query(8, le=25),
    db: Session = Depends(get_db),
    _user=Depends(optional_user),
) -> list[dict[str, Any]]:
    """Peer companies in the same industry/sector."""
    return QuotesDomainService(db).get_peers(ticker, limit=limit)
