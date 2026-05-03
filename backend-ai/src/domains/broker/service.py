"""Broker connect + portfolio sync (Zerodha Kite to start).

Flow:
1. ``connect_zerodha`` returns the Kite OAuth login URL.
2. The browser redirects to ``GET /broker/zerodha/callback?request_token=...``.
3. We exchange the request token for an access token, persist it onto the
   user's primary portfolio (creating one if necessary).
4. ``sync_portfolio`` calls ``KiteClient.get_holdings`` and upserts
   `holdings` + writes a `transactions` row per holding.

Notes:
- Access tokens are stored on the Portfolio row's ``broker_account_id``
  field as ``"<kite_user_id>:<access_token>"``. A real production build
  should use a dedicated `broker_credentials` table with encryption at
  rest. Tracked as a follow-up.
- Symbols come back as Zerodha tradingsymbols (e.g. "INFY"). We resolve
  to a Company by ticker_nse first, then ticker_bse.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.db.models import Company, Holding, Portfolio, Transaction
from src.integrations.market_data.providers.Kite_api.client import KiteClient

logger = logging.getLogger(__name__)


class BrokerService:
    """Read-side wrapper around the Kite Connect API."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    #  Auth flow
    # ------------------------------------------------------------------

    def get_zerodha_login_url(self) -> dict[str, str]:
        client = KiteClient()
        if not client.api_key:
            raise HTTPException(
                status_code=500, detail="KITE_API_KEY is not configured"
            )
        return {"login_url": client.get_login_url()}

    def handle_zerodha_callback(
        self, *, user_id: UUID, request_token: str
    ) -> dict[str, Any]:
        client = KiteClient()
        if not client.api_key:
            raise HTTPException(
                status_code=500, detail="KITE_API_KEY is not configured"
            )
        try:
            data = asyncio.run(client.exchange_request_token(request_token))
        except Exception as exc:
            logger.exception("Kite token exchange failed: %s", exc)
            raise HTTPException(
                status_code=502, detail=f"Kite token exchange failed: {exc}"
            )

        access_token = data.get("access_token")
        kite_user_id = data.get("user_id")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access_token from Kite")

        # Reuse or create a primary portfolio for this user.
        portfolio = (
            self.db.query(Portfolio)
            .filter(
                Portfolio.user_id == user_id,
                Portfolio.broker == "zerodha",
            )
            .first()
        )
        if portfolio is None:
            portfolio = Portfolio(
                user_id=user_id,
                name="Zerodha",
                broker="zerodha",
                is_primary=True,
            )
            self.db.add(portfolio)

        portfolio.broker_account_id = f"{kite_user_id or 'unknown'}:{access_token}"
        self.db.commit()
        self.db.refresh(portfolio)
        return {
            "portfolio_id": str(portfolio.id),
            "kite_user_id": kite_user_id,
            "user_name": data.get("user_name"),
        }

    # ------------------------------------------------------------------
    #  Holdings sync
    # ------------------------------------------------------------------

    def _client_for(self, portfolio: Portfolio) -> KiteClient:
        if portfolio.broker != "zerodha":
            raise HTTPException(
                status_code=400,
                detail=f"Broker {portfolio.broker} not yet supported",
            )
        if not portfolio.broker_account_id or ":" not in portfolio.broker_account_id:
            raise HTTPException(
                status_code=400,
                detail="Portfolio has no broker access token. Re-connect via OAuth.",
            )
        _, access_token = portfolio.broker_account_id.split(":", 1)
        return KiteClient(access_token=access_token)

    def _resolve_company(self, symbol: str, exchange: Optional[str]) -> Optional[Company]:
        upper = symbol.upper()
        q = self.db.query(Company)
        if exchange and exchange.upper() == "BSE":
            company = q.filter(Company.ticker_bse == upper).first()
            if company:
                return company
        company = q.filter(Company.ticker_nse == upper).first()
        if company:
            return company
        return q.filter(Company.ticker_bse == upper).first()

    def sync_portfolio(self, portfolio_id: UUID) -> dict[str, Any]:
        portfolio = (
            self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        )
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        client = self._client_for(portfolio)

        try:
            raw = asyncio.run(client.get_holdings())
        except Exception as exc:
            logger.exception("Kite holdings fetch failed: %s", exc)
            raise HTTPException(
                status_code=502, detail=f"Broker holdings fetch failed: {exc}"
            )

        upserted = 0
        skipped = 0
        for row in raw:
            symbol = (row.get("tradingsymbol") or "").strip()
            exchange = (row.get("exchange") or "").strip()
            qty_raw = row.get("quantity") or row.get("opening_quantity") or 0
            avg = row.get("average_price")
            if not symbol or not qty_raw:
                skipped += 1
                continue
            company = self._resolve_company(symbol, exchange)
            if company is None:
                skipped += 1
                logger.debug("No company for symbol=%s exchange=%s", symbol, exchange)
                continue
            try:
                qty = Decimal(str(qty_raw))
                avg_price = Decimal(str(avg)) if avg is not None else None
            except Exception:
                skipped += 1
                continue

            holding = (
                self.db.query(Holding)
                .filter(
                    Holding.portfolio_id == portfolio.id,
                    Holding.company_id == company.id,
                )
                .first()
            )
            if holding is None:
                holding = Holding(
                    portfolio_id=portfolio.id,
                    company_id=company.id,
                    quantity=qty,
                )
                self.db.add(holding)
            else:
                holding.quantity = qty
            if avg_price is not None and hasattr(holding, "average_price"):
                holding.average_price = avg_price

            # Idempotent transaction log: keyed by broker_txn_id derived
            # from a stable hash of (symbol, qty, avg).
            broker_txn_id = (
                f"kite-snapshot:{symbol}:{qty}:{avg_price if avg_price else 0}"
            )
            existing_txn = (
                self.db.query(Transaction)
                .filter(
                    Transaction.portfolio_id == portfolio.id,
                    Transaction.broker_txn_id == broker_txn_id,
                )
                .first()
            )
            if existing_txn is None:
                self.db.add(
                    Transaction(
                        portfolio_id=portfolio.id,
                        company_id=company.id,
                        txn_type="snapshot",
                        txn_date=date.today(),
                        quantity=qty,
                        price_inr=avg_price,
                        broker_txn_id=broker_txn_id,
                        source="kite_holdings_sync",
                    )
                )
            upserted += 1

        portfolio.updated_at = datetime.utcnow()
        self.db.commit()
        return {
            "portfolio_id": str(portfolio.id),
            "broker": portfolio.broker,
            "synced": upserted,
            "skipped": skipped,
        }
