"""
FastAPI routes for Upstox v2 API endpoints
Indian markets: NSE, BSE, MCX, NFO, CDS
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from typing import Optional, List
from datetime import date, timedelta

from .client import UpstoxClient
from .models import (
    PlaceOrderRequest, ModifyOrderRequest,
    UpstoxResponse,
)

router = APIRouter(prefix="/upstox", tags=["Upstox API (Indian Markets)"])

# Initialize Upstox client (reads UPSTOX_ACCESS_TOKEN from env)
upstox_client = UpstoxClient()


# ------------------------------------------------------------------ #
#  Authentication helpers                                              #
# ------------------------------------------------------------------ #

@router.get(
    "/auth/login-url",
    summary="Get OAuth2 login URL",
    description=(
        "Returns the URL to redirect a user to for Upstox OAuth2 login. "
        "After the user logs in, Upstox redirects to `redirect_uri?code=<auth_code>`. "
        "Pass that code to `/auth/token`."
    ),
)
async def get_login_url(
    redirect_uri: str = Query(..., description="URL registered in your Upstox app"),
    state: Optional[str] = Query(None, description="Optional CSRF state string"),
):
    """Generate the Upstox OAuth2 authorization URL."""
    try:
        url = upstox_client.get_login_url(redirect_uri=redirect_uri, state=state)
        return {"status": "success", "login_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/auth/token",
    summary="Exchange auth code for access token",
    description=(
        "Exchange the authorization `code` (received after user login) "
        "for an `access_token`. Requires `UPSTOX_API_KEY` and `UPSTOX_API_SECRET` "
        "to be set in the environment."
    ),
)
async def exchange_code_for_token(
    code: str = Body(..., embed=True, description="Auth code from redirect URL"),
    redirect_uri: str = Body(..., embed=True, description="Same URI used during login"),
):
    """Exchange an auth code for an Upstox access token."""
    try:
        data = await upstox_client.exchange_code_for_token(code=code, redirect_uri=redirect_uri)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  User                                                                #
# ------------------------------------------------------------------ #

@router.get(
    "/user/profile",
    summary="Get user profile",
)
async def get_user_profile():
    """Retrieve the authenticated user's profile (name, email, exchanges, etc.)."""
    try:
        return await upstox_client.get_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/user/funds",
    summary="Get funds and margin",
)
async def get_funds_and_margin(
    segment: Optional[str] = Query(
        None,
        description="SEC (equity) or COM (commodity). Omit for all.",
        pattern="^(SEC|COM)$",
    ),
):
    """Retrieve available funds and margin details per segment."""
    try:
        return await upstox_client.get_fund_and_margin(segment=segment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Market Quotes                                                       #
# ------------------------------------------------------------------ #

@router.get(
    "/market-quote/full",
    summary="Full market quotes",
    description=(
        "Get complete market snapshot (OHLC, depth, LTP, volume, OI, circuit limits) "
        "for up to 500 instruments.\n\n"
        "**Instrument key format:** `{EXCHANGE}_{SEGMENT}|{ISIN}`  \n"
        "Examples: `NSE_EQ|INE848E01016`, `BSE_EQ|INE062A01020`, `NSE_INDEX|Nifty 50`"
    ),
)
async def get_full_market_quotes(
    instrument_keys: str = Query(
        ...,
        description="Comma-separated instrument keys. E.g. NSE_EQ|INE848E01016,BSE_EQ|INE062A01020",
    ),
):
    """Full market quotes including order book depth for multiple instruments."""
    try:
        keys = [k.strip() for k in instrument_keys.split(",")]
        return await upstox_client.get_full_market_quote(keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/market-quote/ohlc",
    summary="OHLC quotes",
)
async def get_ohlc_quotes(
    instrument_keys: str = Query(..., description="Comma-separated instrument keys"),
    interval: str = Query(
        "1d",
        description="Candle interval: 1d (daily), I1 (1-min), I30 (30-min)",
    ),
):
    """Get OHLC quotes snapshot for multiple instruments."""
    try:
        keys = [k.strip() for k in instrument_keys.split(",")]
        return await upstox_client.get_ohlc_quote(keys, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/market-quote/ltp",
    summary="Last Traded Price (LTP)",
)
async def get_ltp_quotes(
    instrument_keys: str = Query(..., description="Comma-separated instrument keys"),
):
    """Get the most recent traded price for multiple instruments."""
    try:
        keys = [k.strip() for k in instrument_keys.split(",")]
        return await upstox_client.get_ltp_quote(keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/market-quote/option-greeks",
    summary="Option Greeks",
)
async def get_option_greeks(
    instrument_keys: str = Query(..., description="Comma-separated F&O instrument keys"),
):
    """Get Delta, Gamma, Theta, Vega, and Implied Volatility for option instruments."""
    try:
        keys = [k.strip() for k in instrument_keys.split(",")]
        return await upstox_client.get_option_greeks(keys)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Historical & Intraday Candle Data                                   #
# ------------------------------------------------------------------ #

@router.get(
    "/historical/{instrument_key:path}/{interval}",
    summary="Historical candle data",
    description=(
        "Retrieve OHLCV candle data for an instrument.\n\n"
        "**Intervals & available history:**\n"
        "- `1minute` → last 6 months\n"
        "- `30minute` → last 6 months\n"
        "- `day` → last 1 year\n"
        "- `week` → last 10 years\n"
        "- `month` → last 10 years\n\n"
        "Candle array format: `[timestamp, open, high, low, close, volume, oi]`"
    ),
)
async def get_historical_candle(
    instrument_key: str = Path(..., description="Instrument key (URL-encode the | as %7C if needed)"),
    interval: str = Path(..., description="1minute | 30minute | day | week | month"),
    to_date: str = Query(
        ...,
        description="End date inclusive (YYYY-MM-DD)",
    ),
    from_date: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD). Optional.",
    ),
):
    """Fetch OHLCV historical candles for a single instrument."""
    try:
        return await upstox_client.get_historical_candle(
            instrument_key=instrument_key,
            interval=interval,
            to_date=to_date,
            from_date=from_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/intraday/{instrument_key:path}/{interval}",
    summary="Intraday candle data (today)",
    description="Get intraday candles for the current trading session.",
)
async def get_intraday_candle(
    instrument_key: str = Path(..., description="Instrument key"),
    interval: str = Path(..., description="1minute | 30minute"),
):
    """Fetch intraday OHLCV candles for today's session."""
    try:
        return await upstox_client.get_intraday_candle(
            instrument_key=instrument_key,
            interval=interval,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Portfolio                                                           #
# ------------------------------------------------------------------ #

@router.get(
    "/portfolio/holdings",
    summary="Get long-term holdings",
)
async def get_holdings():
    """Get all equity delivery holdings for the authenticated user."""
    try:
        return await upstox_client.get_holdings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/portfolio/positions",
    summary="Get short-term positions",
)
async def get_positions():
    """Get open intraday and F&O positions for today."""
    try:
        return await upstox_client.get_positions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/portfolio/convert-position",
    summary="Convert position type",
)
async def convert_position(
    instrument_key: str = Body(..., embed=True, description="Instrument key"),
    new_product: str = Body(..., embed=True, description="Target product: D or I"),
    old_product: str = Body(..., embed=True, description="Current product: D or I"),
    transaction_type: str = Body(..., embed=True, description="BUY or SELL"),
    quantity: int = Body(..., embed=True, description="Quantity to convert"),
):
    """Convert an open position from intraday (I) to delivery (D) or vice-versa."""
    try:
        return await upstox_client.convert_position(
            instrument_key=instrument_key,
            new_product=new_product,
            old_product=old_product,
            transaction_type=transaction_type,
            quantity=quantity,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Orders                                                              #
# ------------------------------------------------------------------ #

@router.get(
    "/orders",
    summary="Get order book",
)
async def get_order_book():
    """Retrieve all orders placed today."""
    try:
        return await upstox_client.get_order_book()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/orders/{order_id}",
    summary="Get order details",
)
async def get_order_details(
    order_id: str = Path(..., description="Upstox order ID"),
):
    """Get full details for a specific order."""
    try:
        return await upstox_client.get_order_details(order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/orders/{order_id}/history",
    summary="Get order history",
)
async def get_order_history(
    order_id: str = Path(..., description="Upstox order ID"),
):
    """Get the full audit trail / history of an order."""
    try:
        return await upstox_client.get_order_history(order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/trades",
    summary="Get today's trades",
)
async def get_trades():
    """Retrieve all executed trades for the current trading day."""
    try:
        return await upstox_client.get_trades()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/orders",
    summary="Place order",
    description=(
        "Place a new order on NSE/BSE/MCX/NFO/CDS.\n\n"
        "**order_type values:** `MARKET`, `LIMIT`, `SL`, `SL-M`\n\n"
        "**product values:** `D` (delivery), `I` (intraday), `CO` (cover order)\n\n"
        "**Instrument key format:** `NSE_EQ|INE848E01016`"
    ),
)
async def place_order(order: PlaceOrderRequest):
    """Place a new buy or sell order."""
    try:
        return await upstox_client.place_order(
            instrument_key=order.instrument_key,
            transaction_type=order.transaction_type,
            quantity=order.quantity,
            order_type=order.order_type,
            product=order.product,
            price=order.price,
            trigger_price=order.trigger_price,
            disclosed_quantity=order.disclosed_quantity,
            validity=order.validity,
            is_amo=order.is_amo,
            tag=order.tag,
            slice=order.slice,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/orders",
    summary="Modify order",
)
async def modify_order(order: ModifyOrderRequest):
    """Modify fields of an existing open/pending order."""
    try:
        return await upstox_client.modify_order(
            order_id=order.order_id,
            quantity=order.quantity,
            price=order.price,
            order_type=order.order_type,
            trigger_price=order.trigger_price,
            validity=order.validity,
            disclosed_quantity=order.disclosed_quantity,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/orders/{order_id}",
    summary="Cancel order",
)
async def cancel_order(
    order_id: str = Path(..., description="Upstox order ID to cancel"),
):
    """Cancel an open or pending order."""
    try:
        return await upstox_client.cancel_order(order_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Option Chain                                                        #
# ------------------------------------------------------------------ #

@router.get(
    "/options/contracts",
    summary="Get option contracts",
    description=(
        "List available option contracts for an underlying instrument.\n\n"
        "**Common index keys:** `NSE_INDEX|Nifty 50`, `NSE_INDEX|Nifty Bank`"
    ),
)
async def get_option_contracts(
    instrument_key: str = Query(
        ...,
        description="Underlying instrument key (e.g. NSE_INDEX|Nifty 50)",
    ),
    expiry_date: Optional[str] = Query(
        None,
        description="Filter by expiry date (YYYY-MM-DD)",
    ),
):
    """List option contracts for a given underlying (with optional expiry filter)."""
    try:
        return await upstox_client.get_option_contracts(
            instrument_key=instrument_key,
            expiry_date=expiry_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/options/chain",
    summary="Get option chain",
)
async def get_option_chain(
    instrument_key: str = Query(
        ...,
        description="Underlying instrument key (e.g. NSE_INDEX|Nifty 50)",
    ),
    expiry_date: str = Query(..., description="Expiry date (YYYY-MM-DD)"),
):
    """Get the full option chain with Greeks for a given underlying and expiry date."""
    try:
        return await upstox_client.get_option_chain(
            instrument_key=instrument_key,
            expiry_date=expiry_date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Market Status                                                       #
# ------------------------------------------------------------------ #

@router.get(
    "/market/status",
    summary="Get market / exchange status",
)
async def get_market_status(
    exchange: Optional[str] = Query(
        None,
        description="Exchange code: NSE, BSE, MCX. Omit for all.",
    ),
):
    """Check whether exchanges are open or closed right now."""
    try:
        return await upstox_client.get_market_status(exchange=exchange)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Charges                                                             #
# ------------------------------------------------------------------ #

@router.get(
    "/charges/brokerage",
    summary="Estimate brokerage charges",
)
async def get_brokerage_charges(
    instrument_key: str = Query(..., description="Instrument key"),
    quantity: int = Query(..., description="Number of shares/lots", gt=0),
    price: float = Query(..., description="Trade price", gt=0),
    transaction_type: str = Query(..., description="BUY or SELL"),
    product: str = Query(..., description="D (delivery), I (intraday), CO (cover order)"),
):
    """Get an estimated breakdown of brokerage, STT, GST, and other charges."""
    try:
        return await upstox_client.get_brokerage_charges(
            instrument_key=instrument_key,
            quantity=quantity,
            price=price,
            transaction_type=transaction_type,
            product=product,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
