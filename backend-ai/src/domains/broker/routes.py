"""Broker connect + portfolio sync API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import Portfolio, User
from src.domains.auth.dependencies import assert_self, get_current_user
from src.domains.broker.service import BrokerService
from fastapi import HTTPException

router = APIRouter(prefix="/broker", tags=["broker"])


class ZerodhaCallbackRequest(BaseModel):
    user_id: UUID
    request_token: str


@router.get("/zerodha/login-url")
def zerodha_login_url(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return the Kite Connect OAuth login URL the user should be sent to."""
    return BrokerService(db).get_zerodha_login_url()


@router.post("/zerodha/callback")
def zerodha_callback(
    payload: ZerodhaCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange the request_token from the Kite redirect for an access token
    and bind it to the user's Zerodha portfolio."""
    assert_self(payload.user_id, current_user)
    return BrokerService(db).handle_zerodha_callback(
        user_id=payload.user_id, request_token=payload.request_token
    )


@router.get("/zerodha/callback")
def zerodha_callback_get(
    request_token: str = Query(...),
    user_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convenience GET endpoint that mirrors the POST callback so the Kite
    redirect (which uses GET) lands directly here."""
    assert_self(user_id, current_user)
    return BrokerService(db).handle_zerodha_callback(
        user_id=user_id, request_token=request_token
    )


@router.post("/portfolios/{portfolio_id}/sync")
def sync_portfolio(
    portfolio_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pull current holdings from the broker and upsert into our DB."""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your portfolio")
    return BrokerService(db).sync_portfolio(portfolio_id)
