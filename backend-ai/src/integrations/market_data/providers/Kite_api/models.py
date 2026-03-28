"""
Pydantic models for Kite Connect API responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ------------------------------------------------------------------
# Market Quote Models
# ------------------------------------------------------------------

class LTPData(BaseModel):
    """Last Traded Price data for a single instrument."""
    instrument_token: Optional[int] = Field(None, description="Unique instrument token")
    last_price: Optional[float] = Field(None, description="Last traded price")


class OHLCData(BaseModel):
    """Open/High/Low/Close data."""
    open: Optional[float] = Field(None, description="Open price")
    high: Optional[float] = Field(None, description="High price")
    low: Optional[float] = Field(None, description="Low price")
    close: Optional[float] = Field(None, description="Previous close / close price")


class OHLCQuote(BaseModel):
    """OHLC quote for a single instrument (free-tier quote endpoint)."""
    instrument_token: Optional[int] = Field(None, description="Unique instrument token")
    last_price: Optional[float] = Field(None, description="Last traded price")
    ohlc: Optional[OHLCData] = None


class DepthItem(BaseModel):
    """Single bid/ask entry in market depth."""
    price: Optional[float] = None
    quantity: Optional[int] = None
    orders: Optional[int] = None


class MarketDepth(BaseModel):
    """Order book depth (buy and sell sides)."""
    buy: Optional[List[DepthItem]] = None
    sell: Optional[List[DepthItem]] = None


class FullQuote(BaseModel):
    """Full market quote for a single instrument."""
    instrument_token: Optional[int] = Field(None, description="Unique instrument token")
    timestamp: Optional[str] = Field(None, description="Last quote timestamp")
    last_trade_time: Optional[str] = Field(None, description="Last trade time")
    last_price: Optional[float] = Field(None, description="Last traded price")
    last_quantity: Optional[int] = Field(None, description="Last traded quantity")
    buy_quantity: Optional[int] = Field(None, description="Total pending buy quantity")
    sell_quantity: Optional[int] = Field(None, description="Total pending sell quantity")
    volume: Optional[int] = Field(None, description="Volume traded today")
    average_price: Optional[float] = Field(None, description="Average trade price today")
    oi: Optional[int] = Field(None, description="Open interest (F&O)")
    oi_day_high: Optional[int] = Field(None, description="OI day high")
    oi_day_low: Optional[int] = Field(None, description="OI day low")
    net_change: Optional[float] = Field(None, description="Net change from previous close")
    lower_circuit_limit: Optional[float] = Field(None, description="Lower circuit limit")
    upper_circuit_limit: Optional[float] = Field(None, description="Upper circuit limit")
    ohlc: Optional[OHLCData] = None
    depth: Optional[MarketDepth] = None


# ------------------------------------------------------------------
# Instrument Master Models
# ------------------------------------------------------------------

class Instrument(BaseModel):
    """A single row from the Kite instruments master CSV."""
    instrument_token: Optional[str] = Field(None, description="Unique instrument token")
    exchange_token: Optional[str] = Field(None, description="Exchange-level token")
    tradingsymbol: Optional[str] = Field(None, description="Trading symbol")
    name: Optional[str] = Field(None, description="Company / contract name")
    last_price: Optional[str] = Field(None, description="Last known price (may be stale)")
    expiry: Optional[str] = Field(None, description="Expiry date for F&O instruments")
    strike: Optional[str] = Field(None, description="Strike price for options")
    tick_size: Optional[str] = Field(None, description="Minimum price movement")
    lot_size: Optional[str] = Field(None, description="Market lot size")
    instrument_type: Optional[str] = Field(None, description="EQ, FUT, CE, PE, etc.")
    segment: Optional[str] = Field(None, description="Market segment")
    exchange: Optional[str] = Field(None, description="Exchange name")


# ------------------------------------------------------------------
# Generic response wrappers
# ------------------------------------------------------------------

class LTPResponse(BaseModel):
    """Response for GET /kite/quote/ltp."""
    data: Dict[str, LTPData] = Field(default_factory=dict)


class OHLCResponse(BaseModel):
    """Response for GET /kite/quote/ohlc."""
    data: Dict[str, OHLCQuote] = Field(default_factory=dict)


class QuoteResponse(BaseModel):
    """Response for GET /kite/quote."""
    data: Dict[str, FullQuote] = Field(default_factory=dict)


class InstrumentsResponse(BaseModel):
    """Response for GET /kite/instruments."""
    count: int = Field(..., description="Total number of instruments returned")
    instruments: List[Instrument]


class LoginUrlResponse(BaseModel):
    """Response for GET /kite/login-url."""
    login_url: str = Field(..., description="Kite Connect OAuth2 login URL")
