"""
FastAPI routes for Kite Connect API — free-tier, GET-only endpoints.
Reference: https://kite.trade/docs/connect/v3/
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from .client import KiteClient
from .models import (
    LTPResponse,
    LTPData,
    OHLCResponse,
    OHLCQuote,
    QuoteResponse,
    FullQuote,
    InstrumentsResponse,
    Instrument,
    LoginUrlResponse,
    OHLCData,
    MarketDepth,
    DepthItem,
)

router = APIRouter(prefix="/kite", tags=["Kite Connect"])

# Initialise shared client (picks up env vars automatically)
kite_client = KiteClient()


# ------------------------------------------------------------------
# Auth helpers  (read-only — no token exchange write)
# ------------------------------------------------------------------

@router.get(
    "/login-url",
    response_model=LoginUrlResponse,
    summary="Get Kite Connect OAuth2 login URL",
)
async def get_login_url():
    """
    Returns the Kite Connect OAuth2 login URL.
    Redirect the user to this URL so they can authorise the app and receive
    a `request_token` at your registered redirect URI.

    **No credentials are written — this is purely a read/helper endpoint.**
    """
    return LoginUrlResponse(login_url=kite_client.get_login_url())


# ------------------------------------------------------------------
# Market Quotes  (free tier)
# ------------------------------------------------------------------

@router.get(
    "/quote/ltp",
    response_model=LTPResponse,
    summary="Last Traded Price for one or more instruments",
)
async def get_ltp(
    instruments: List[str] = Query(
        ...,
        alias="i",
        description=(
            'One or more instruments in "EXCHANGE:TRADINGSYMBOL" format. '
            "Example: i=NSE:INFY&i=BSE:RELIANCE"
        ),
        example=["NSE:INFY", "NSE:RELIANCE"],
    ),
):
    """
    Fetch the **Last Traded Price** for one or more instruments.

    Pass each instrument as a separate `i` query parameter:
    ```
    GET /kite/quote/ltp?i=NSE:INFY&i=NSE:TCS
    ```
    """
    try:
        raw = await kite_client.get_ltp(instruments)
        data = {
            key: LTPData(
                instrument_token=val.get("instrument_token"),
                last_price=val.get("last_price"),
            )
            for key, val in raw.items()
        }
        return LTPResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/quote/ohlc",
    response_model=OHLCResponse,
    summary="OHLC + LTP for one or more instruments",
)
async def get_ohlc(
    instruments: List[str] = Query(
        ...,
        alias="i",
        description=(
            'One or more instruments in "EXCHANGE:TRADINGSYMBOL" format. '
            "Example: i=NSE:INFY&i=BSE:RELIANCE"
        ),
        example=["NSE:INFY", "NSE:RELIANCE"],
    ),
):
    """
    Fetch **OHLC** (Open, High, Low, Close) data along with the last traded price
    for one or more instruments.

    Pass each instrument as a separate `i` query parameter:
    ```
    GET /kite/quote/ohlc?i=NSE:INFY&i=NSE:TCS
    ```
    """
    try:
        raw = await kite_client.get_ohlc(instruments)
        data = {}
        for key, val in raw.items():
            ohlc_raw = val.get("ohlc") or {}
            data[key] = OHLCQuote(
                instrument_token=val.get("instrument_token"),
                last_price=val.get("last_price"),
                ohlc=OHLCData(
                    open=ohlc_raw.get("open"),
                    high=ohlc_raw.get("high"),
                    low=ohlc_raw.get("low"),
                    close=ohlc_raw.get("close"),
                ),
            )
        return OHLCResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/quote",
    response_model=QuoteResponse,
    summary="Full market depth quote for one or more instruments",
)
async def get_quote(
    instruments: List[str] = Query(
        ...,
        alias="i",
        description=(
            'One or more instruments in "EXCHANGE:TRADINGSYMBOL" format. '
            "Example: i=NSE:INFY&i=BSE:RELIANCE"
        ),
        example=["NSE:INFY"],
    ),
):
    """
    Fetch a **full market quote** including OHLC, volume, OI, circuit limits,
    and 5-level market depth (bid/ask order book) for one or more instruments.

    Pass each instrument as a separate `i` query parameter:
    ```
    GET /kite/quote?i=NSE:INFY&i=NSE:TCS
    ```
    """
    try:
        raw = await kite_client.get_quote(instruments)
        data = {}
        for key, val in raw.items():
            ohlc_raw = val.get("ohlc") or {}
            depth_raw = val.get("depth") or {}

            buy_depth = [
                DepthItem(
                    price=b.get("price"),
                    quantity=b.get("quantity"),
                    orders=b.get("orders"),
                )
                for b in depth_raw.get("buy", [])
            ]
            sell_depth = [
                DepthItem(
                    price=s.get("price"),
                    quantity=s.get("quantity"),
                    orders=s.get("orders"),
                )
                for s in depth_raw.get("sell", [])
            ]

            data[key] = FullQuote(
                instrument_token=val.get("instrument_token"),
                timestamp=val.get("timestamp"),
                last_trade_time=val.get("last_trade_time"),
                last_price=val.get("last_price"),
                last_quantity=val.get("last_quantity"),
                buy_quantity=val.get("buy_quantity"),
                sell_quantity=val.get("sell_quantity"),
                volume=val.get("volume"),
                average_price=val.get("average_price"),
                oi=val.get("oi"),
                oi_day_high=val.get("oi_day_high"),
                oi_day_low=val.get("oi_day_low"),
                net_change=val.get("net_change"),
                lower_circuit_limit=val.get("lower_circuit_limit"),
                upper_circuit_limit=val.get("upper_circuit_limit"),
                ohlc=OHLCData(
                    open=ohlc_raw.get("open"),
                    high=ohlc_raw.get("high"),
                    low=ohlc_raw.get("low"),
                    close=ohlc_raw.get("close"),
                ),
                depth=MarketDepth(buy=buy_depth, sell=sell_depth),
            )
        return QuoteResponse(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------
# Instruments master  (free tier)
# ------------------------------------------------------------------

@router.get(
    "/instruments",
    response_model=InstrumentsResponse,
    summary="All tradable instruments across all exchanges",
)
async def get_all_instruments(
    limit: Optional[int] = Query(
        None,
        description="Limit the number of instruments returned (useful for testing).",
        ge=1,
    ),
):
    """
    Download the **complete instruments master** CSV from Kite and return it as JSON.

    This dump covers all exchanges (NSE, BSE, NFO, CDS, BFO, MCX, …) and contains
    instrument tokens, trading symbols, expiry dates, strike prices, lot sizes, etc.

    > Note: The file is large (~1 MB). Use the `limit` parameter for quick lookups.
    """
    try:
        instruments = await kite_client.get_instruments()
        if limit:
            instruments = instruments[:limit]
        return InstrumentsResponse(
            count=len(instruments),
            instruments=[Instrument(**inst) for inst in instruments],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/instruments/{exchange}",
    response_model=InstrumentsResponse,
    summary="Tradable instruments filtered by exchange",
)
async def get_instruments_by_exchange(
    exchange: str,
    limit: Optional[int] = Query(
        None,
        description="Limit the number of instruments returned.",
        ge=1,
    ),
):
    """
    Download the instruments master for a **specific exchange** (e.g. `NSE`, `BSE`,
    `NFO`, `CDS`, `BFO`, `MCX`) and return it as JSON.

    Exchange codes:
    | Code | Description |
    |------|-------------|
    | NSE  | National Stock Exchange |
    | BSE  | Bombay Stock Exchange |
    | NFO  | NSE Futures & Options |
    | CDS  | Currency Derivatives |
    | BFO  | BSE Futures & Options |
    | MCX  | Multi Commodity Exchange |
    """
    try:
        instruments = await kite_client.get_instruments(exchange.upper())
        if limit:
            instruments = instruments[:limit]
        return InstrumentsResponse(
            count=len(instruments),
            instruments=[Instrument(**inst) for inst in instruments],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
