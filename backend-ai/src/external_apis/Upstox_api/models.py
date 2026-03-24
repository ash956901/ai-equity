"""
Pydantic models for Upstox API v2 responses
Covers Indian markets: NSE, BSE, MCX, NFO, CDS
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# ==================== Shared / Wrapper ====================

class UpstoxResponse(BaseModel):
    """Generic Upstox API response wrapper"""
    status: str = Field(..., description="'success' or 'error'")
    data: Optional[Any] = Field(None, description="Response payload")


# ==================== User ====================

class UserProfile(BaseModel):
    """Upstox user profile information"""
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    email: Optional[str] = None
    user_type: Optional[str] = None
    broker: Optional[str] = None
    exchanges: Optional[List[str]] = None
    products: Optional[List[str]] = None
    order_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


class FundSegment(BaseModel):
    """Individual fund/margin segment data"""
    used_margin: Optional[float] = None
    payin_amount: Optional[float] = None
    span_margin: Optional[float] = None
    adhoc_margin: Optional[float] = None
    notional_cash: Optional[float] = None
    available_margin: Optional[float] = None
    exposure_margin: Optional[float] = None


class FundsAndMargin(BaseModel):
    """Funds and margin response"""
    equity: Optional[FundSegment] = None
    commodity: Optional[FundSegment] = None


# ==================== Market Quotes ====================

class OHLC(BaseModel):
    """OHLC price data"""
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None


class DepthEntry(BaseModel):
    """Single bid/ask depth entry"""
    quantity: Optional[int] = None
    price: Optional[float] = None
    orders: Optional[int] = None


class MarketDepth(BaseModel):
    """Top 5 buy/sell market depth"""
    buy: Optional[List[DepthEntry]] = None
    sell: Optional[List[DepthEntry]] = None


class FullMarketQuote(BaseModel):
    """Full market quote for a single instrument"""
    ohlc: Optional[OHLC] = None
    depth: Optional[MarketDepth] = None
    timestamp: Optional[str] = None
    instrument_token: Optional[str] = None
    symbol: Optional[str] = None
    last_price: Optional[float] = None
    volume: Optional[int] = None
    average_price: Optional[float] = None
    oi: Optional[float] = None
    net_change: Optional[float] = None
    total_buy_quantity: Optional[float] = None
    total_sell_quantity: Optional[float] = None
    lower_circuit_limit: Optional[float] = None
    upper_circuit_limit: Optional[float] = None
    last_trade_time: Optional[str] = None
    oi_day_high: Optional[float] = None
    oi_day_low: Optional[float] = None


class OHLCQuote(BaseModel):
    """OHLC snapshot quote"""
    instrument_token: Optional[str] = None
    last_price: Optional[float] = None
    ohlc: Optional[OHLC] = None


class LTPQuote(BaseModel):
    """Last Traded Price (LTP) quote"""
    instrument_token: Optional[str] = None
    last_price: Optional[float] = None


class OptionGreeks(BaseModel):
    """Option Greeks data"""
    instrument_token: Optional[str] = None
    last_price: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    implied_volatility: Optional[float] = None


# ==================== Historical / Intraday Candle ====================

class CandleData(BaseModel):
    """
    Parsed candle data from Upstox.

    Upstox returns candles as arrays:
      [timestamp, open, high, low, close, volume, oi]
    This model provides named fields for convenience.
    """
    timestamp: Optional[str] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[float] = None

    @classmethod
    def from_array(cls, arr: List[Any]) -> "CandleData":
        """
        Build a CandleData from a raw Upstox candle array.

        Args:
            arr: ``[timestamp, open, high, low, close, volume, oi]``
        """
        return cls(
            timestamp=arr[0] if len(arr) > 0 else None,
            open=arr[1] if len(arr) > 1 else None,
            high=arr[2] if len(arr) > 2 else None,
            low=arr[3] if len(arr) > 3 else None,
            close=arr[4] if len(arr) > 4 else None,
            volume=arr[5] if len(arr) > 5 else None,
            open_interest=arr[6] if len(arr) > 6 else None,
        )


# ==================== Portfolio ====================

class Holding(BaseModel):
    """Long-term holding (delivery)"""
    isin: Optional[str] = None
    instrument_token: Optional[str] = None
    trading_symbol: Optional[str] = None
    exchange: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    t1_quantity: Optional[int] = None
    average_price: Optional[float] = None
    last_price: Optional[float] = None
    close_price: Optional[float] = None
    pnl: Optional[float] = None
    day_change: Optional[float] = None
    day_change_percentage: Optional[float] = None


class Position(BaseModel):
    """Short-term position (intraday / F&O)"""
    exchange: Optional[str] = None
    instrument_token: Optional[str] = None
    trading_symbol: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    overnight_quantity: Optional[int] = None
    average_price: Optional[float] = None
    last_price: Optional[float] = None
    close_price: Optional[float] = None
    buy_price: Optional[float] = None
    sell_price: Optional[float] = None
    buy_value: Optional[float] = None
    sell_value: Optional[float] = None
    value: Optional[float] = None
    pnl: Optional[float] = None
    unrealised: Optional[float] = None
    realised: Optional[float] = None
    multiplier: Optional[float] = None
    day_buy_quantity: Optional[int] = None
    day_sell_quantity: Optional[int] = None
    day_buy_price: Optional[float] = None
    day_sell_price: Optional[float] = None


# ==================== Orders ====================

class Order(BaseModel):
    """Order details"""
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    status: Optional[str] = None
    status_message: Optional[str] = None
    order_timestamp: Optional[str] = None
    exchange_timestamp: Optional[str] = None
    instrument_token: Optional[str] = None
    trading_symbol: Optional[str] = None
    exchange: Optional[str] = None
    product: Optional[str] = None
    order_type: Optional[str] = None
    transaction_type: Optional[str] = None
    validity: Optional[str] = None
    quantity: Optional[int] = None
    pending_quantity: Optional[int] = None
    filled_quantity: Optional[int] = None
    disclosed_quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    average_price: Optional[float] = None
    tag: Optional[str] = None
    is_amo: Optional[bool] = None


class PlaceOrderRequest(BaseModel):
    """Request body for placing an order"""
    instrument_key: str = Field(..., description="Instrument key, e.g. NSE_EQ|INE848E01016")
    transaction_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares/lots")
    order_type: str = Field(..., description="MARKET, LIMIT, SL, SL-M")
    product: str = Field(..., description="D (delivery), I (intraday), CO (cover order)")
    price: float = Field(0.0, description="Limit price (required for LIMIT/SL orders)")
    trigger_price: float = Field(0.0, description="Stop-loss trigger (required for SL/SL-M)")
    disclosed_quantity: int = Field(0, description="Quantity to disclose publicly")
    validity: str = Field("DAY", description="DAY or IOC")
    is_amo: bool = Field(False, description="After Market Order flag")
    tag: Optional[str] = Field(None, description="User-defined tag (max 20 chars)")
    slice: bool = Field(False, description="Auto-slice large orders")


class ModifyOrderRequest(BaseModel):
    """Request body for modifying an order"""
    order_id: str = Field(..., description="Upstox order ID to modify")
    quantity: Optional[int] = None
    price: Optional[float] = None
    order_type: Optional[str] = None
    trigger_price: Optional[float] = None
    validity: Optional[str] = None
    disclosed_quantity: Optional[int] = None


class OrderResponse(BaseModel):
    """Response from place/modify/cancel order"""
    order_id: Optional[str] = None


class Trade(BaseModel):
    """Executed trade record"""
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    trade_id: Optional[str] = None
    instrument_token: Optional[str] = None
    trading_symbol: Optional[str] = None
    exchange: Optional[str] = None
    product: Optional[str] = None
    transaction_type: Optional[str] = None
    quantity: Optional[int] = None
    trade_price: Optional[float] = None
    order_type: Optional[str] = None
    exchange_timestamp: Optional[str] = None


# ==================== Option Chain ====================

class OptionContract(BaseModel):
    """Single option contract metadata"""
    instrument_key: Optional[str] = None
    trading_symbol: Optional[str] = None
    expiry: Optional[str] = None
    strike_price: Optional[float] = None
    option_type: Optional[str] = None  # CE or PE
    lot_size: Optional[int] = None
    tick_size: Optional[float] = None


class OptionChainEntry(BaseModel):
    """Single option chain row (one strike)"""
    expiry: Optional[str] = None
    strike_price: Optional[float] = None
    call_options: Optional[Dict[str, Any]] = None
    put_options: Optional[Dict[str, Any]] = None


# ==================== Market Status ====================

class MarketStatus(BaseModel):
    """Exchange market status"""
    exchange: Optional[str] = None
    segment: Optional[str] = None
    status: Optional[str] = None
    market_status: Optional[str] = None


# ==================== Charges ====================

class BrokerageCharge(BaseModel):
    """Brokerage and statutory charge breakdown"""
    total: Optional[float] = None
    brokerage: Optional[float] = None
    taxes: Optional[Dict[str, Any]] = None
    charges: Optional[Dict[str, Any]] = None
