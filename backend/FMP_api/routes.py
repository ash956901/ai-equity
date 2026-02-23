"""
FastAPI routes for FMP API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from datetime import datetime, date, timedelta

from .client import FMPClient
from .models import *

router = APIRouter(prefix="/fmp", tags=["FMP API"])

# Initialize FMP client
fmp_client = FMPClient()


# ==================== Company Information ====================

@router.get("/company/profile/{symbol}", response_model=List[CompanyProfile])
async def get_company_profile(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get comprehensive company profile information including business description,
    sector, industry, executives, and key statistics.
    """
    try:
        data = await fmp_client.get_company_profile(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}", response_model=List[StockQuote])
async def get_stock_quote(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get real-time stock quote with current price, volume, market cap, and key metrics.
    """
    try:
        data = await fmp_client.get_quote(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quotes", response_model=List[StockQuote])
async def get_multiple_quotes(
    symbols: str = Query(..., description="Comma-separated ticker symbols (e.g., AAPL,MSFT,GOOGL)")
):
    """
    Get real-time quotes for multiple stocks at once.
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        data = await fmp_client.get_quotes(symbol_list)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Historical Price Data ====================

@router.get("/historical/daily/{symbol}")
async def get_historical_daily_prices(
    symbol: str = Path(..., description="Stock ticker symbol"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, description="Number of days to retrieve")
):
    """
    Get historical daily stock prices with OHLCV data.
    """
    try:
        if from_date or to_date:
            data = await fmp_client.get_historical_price(symbol.upper(), from_date, to_date)
        else:
            data = await fmp_client.get_historical_daily(symbol.upper(), limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/historical/intraday/{symbol}")
async def get_intraday_prices(
    symbol: str = Path(..., description="Stock ticker symbol"),
    interval: str = Query("15min", description="Time interval: 1min, 5min, 15min, 30min, 1hour, 4hour"),
    limit: int = Query(100, description="Number of data points to retrieve")
):
    """
    Get intraday historical price data for intraday analysis and trading.
    """
    try:
        valid_intervals = ["1min", "5min", "15min", "30min", "1hour", "4hour"]
        if interval not in valid_intervals:
            raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {valid_intervals}")
        
        data = await fmp_client.get_historical_intraday(symbol.upper(), interval, limit)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Financial Statements ====================

@router.get("/financials/income-statement/{symbol}", response_model=List[IncomeStatement])
async def get_income_statement(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get income statement data including revenue, expenses, and net income.
    """
    try:
        data = await fmp_client.get_income_statement(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financials/balance-sheet/{symbol}", response_model=List[BalanceSheet])
async def get_balance_sheet(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get balance sheet data including assets, liabilities, and equity.
    """
    try:
        data = await fmp_client.get_balance_sheet(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financials/cash-flow/{symbol}", response_model=List[CashFlowStatement])
async def get_cash_flow_statement(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get cash flow statement data including operating, investing, and financing activities.
    """
    try:
        data = await fmp_client.get_cash_flow(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Key Metrics & Ratios ====================

@router.get("/metrics/key-metrics/{symbol}", response_model=List[KeyMetrics])
async def get_key_metrics(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get key financial metrics including P/E ratio, ROE, debt ratios, and more.
    """
    try:
        data = await fmp_client.get_key_metrics(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/financial-ratios/{symbol}", response_model=List[FinancialRatios])
async def get_financial_ratios(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get comprehensive financial ratios for fundamental analysis.
    """
    try:
        data = await fmp_client.get_financial_ratios(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/enterprise-value/{symbol}")
async def get_enterprise_value(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get enterprise value calculations including market cap and debt adjustments.
    """
    try:
        data = await fmp_client.get_enterprise_value(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/financial-growth/{symbol}")
async def get_financial_growth(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get financial growth metrics showing year-over-year and quarter-over-quarter growth rates.
    """
    try:
        data = await fmp_client.get_financial_growth(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Analyst Data & Estimates ====================

@router.get("/analyst/estimates/{symbol}", response_model=List[AnalystEstimates])
async def get_analyst_estimates(
    symbol: str = Path(..., description="Stock ticker symbol"),
    period: str = Query("annual", description="Period: annual or quarter"),
    limit: int = Query(10, description="Number of periods to retrieve")
):
    """
    Get analyst estimates for revenue, EPS, EBITDA, and other metrics.
    """
    try:
        data = await fmp_client.get_analyst_estimates(symbol.upper(), period, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Earnings & Calendar Events ====================

@router.get("/calendar/earnings", response_model=List[EarningsCalendar])
async def get_earnings_calendar(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get earnings calendar with upcoming and past earnings announcements.
    """
    try:
        data = await fmp_client.get_earnings_calendar(from_date, to_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/earnings-surprises/{symbol}", response_model=List[EarningsSurprise])
async def get_earnings_surprises(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get historical earnings surprises comparing actual vs estimated results.
    """
    try:
        data = await fmp_client.get_earnings_surprises(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/ipo", response_model=List[IPOCalendar])
async def get_ipo_calendar(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get IPO calendar with upcoming and recent initial public offerings.
    """
    try:
        data = await fmp_client.get_ipo_calendar(from_date, to_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calendar/dividends")
async def get_dividend_calendar(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get dividend calendar with ex-dividend dates and payment information.
    """
    try:
        data = await fmp_client.get_dividend_calendar(from_date, to_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== News & Press Releases ====================

@router.get("/news/stock", response_model=List[StockNews])
async def get_stock_news(
    symbol: Optional[str] = Query(None, description="Stock ticker symbol (optional for general market news)"),
    limit: int = Query(50, description="Number of news articles to retrieve")
):
    """
    Get latest stock news and market updates.
    """
    try:
        if symbol:
            data = await fmp_client.get_stock_news(symbol.upper(), limit)
        else:
            data = await fmp_client.get_stock_news(None, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news/press-releases/{symbol}", response_model=List[PressRelease])
async def get_press_releases(
    symbol: str = Path(..., description="Stock ticker symbol"),
    limit: int = Query(20, description="Number of press releases to retrieve")
):
    """
    Get official company press releases and announcements.
    """
    try:
        data = await fmp_client.get_press_releases(symbol.upper(), limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Dividends & Corporate Actions ====================

@router.get("/dividends/{symbol}", response_model=List[DividendData])
async def get_dividend_history(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get historical dividend payment data including amounts and dates.
    """
    try:
        data = await fmp_client.get_dividends(symbol.upper())
        if "historical" in data:
            return data["historical"]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock-splits/{symbol}", response_model=List[StockSplit])
async def get_stock_splits(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get historical stock split data.
    """
    try:
        data = await fmp_client.get_stock_splits(symbol.upper())
        if "historical" in data:
            return data["historical"]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Institutional Ownership ====================

@router.get("/ownership/institutional-holders/{symbol}", response_model=List[InstitutionalHolding])
async def get_institutional_holders(
    symbol: str = Path(..., description="Stock ticker symbol")
):
    """
    Get institutional holders and their ownership stakes.
    """
    try:
        data = await fmp_client.get_institutional_holders(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SEC Filings ====================

@router.get("/sec/filings/{symbol}", response_model=List[SECFiling])
async def get_sec_filings(
    symbol: str = Path(..., description="Stock ticker symbol"),
    filing_type: Optional[str] = Query(None, description="Filing type (e.g., 10-K, 10-Q, 8-K)"),
    limit: int = Query(20, description="Number of filings to retrieve")
):
    """
    Get SEC filings including 10-K, 10-Q, 8-K, and other regulatory documents.
    """
    try:
        data = await fmp_client.get_sec_filings(symbol.upper(), filing_type, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Market Data & Screener ====================

@router.get("/market/hours", response_model=MarketHours)
async def get_market_hours():
    """
    Get current market hours and trading status for major exchanges.
    """
    try:
        data = await fmp_client.get_market_hours()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/sector-performance", response_model=List[SectorPerformance])
async def get_sector_performance():
    """
    Get sector performance showing which sectors are outperforming or underperforming.
    """
    try:
        data = await fmp_client.get_sector_performance()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/indexes", response_model=List[MarketIndex])
async def get_market_indexes():
    """
    Get major market indexes like S&P 500, Dow Jones, NASDAQ, etc.
    """
    try:
        data = await fmp_client.get_market_indexes()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/gainers")
async def get_top_gainers():
    """
    Get today's top gaining stocks by percentage change.
    """
    try:
        data = await fmp_client.get_gainers()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/losers")
async def get_top_losers():
    """
    Get today's top losing stocks by percentage change.
    """
    try:
        data = await fmp_client.get_losers()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/most-active")
async def get_most_active():
    """
    Get most actively traded stocks by volume.
    """
    try:
        data = await fmp_client.get_most_active()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener", response_model=List[ScreenerResult])
async def stock_screener(
    market_cap_lower: Optional[int] = Query(None, description="Minimum market cap"),
    market_cap_upper: Optional[int] = Query(None, description="Maximum market cap"),
    price_lower: Optional[float] = Query(None, description="Minimum price"),
    price_upper: Optional[float] = Query(None, description="Maximum price"),
    beta_lower: Optional[float] = Query(None, description="Minimum beta"),
    beta_upper: Optional[float] = Query(None, description="Maximum beta"),
    volume_lower: Optional[int] = Query(None, description="Minimum volume"),
    volume_upper: Optional[int] = Query(None, description="Maximum volume"),
    dividend_lower: Optional[float] = Query(None, description="Minimum dividend yield"),
    dividend_upper: Optional[float] = Query(None, description="Maximum dividend yield"),
    sector: Optional[str] = Query(None, description="Sector filter"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    exchange: Optional[str] = Query(None, description="Exchange filter (e.g., NYSE, NASDAQ)"),
    limit: int = Query(100, description="Maximum results")
):
    """
    Screen stocks based on multiple criteria for quantitative analysis and stock picking.
    """
    try:
        data = await fmp_client.stock_screener(
            market_cap_lower=market_cap_lower,
            market_cap_upper=market_cap_upper,
            price_lower=price_lower,
            price_upper=price_upper,
            beta_lower=beta_lower,
            beta_upper=beta_upper,
            volume_lower=volume_lower,
            volume_upper=volume_upper,
            dividend_lower=dividend_lower,
            dividend_upper=dividend_upper,
            sector=sector,
            industry=industry,
            exchange=exchange,
            limit=limit
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ETF Data ====================

@router.get("/etf/holdings/{symbol}", response_model=List[ETFHolding])
async def get_etf_holdings(
    symbol: str = Path(..., description="ETF ticker symbol")
):
    """
    Get ETF holdings and portfolio composition.
    """
    try:
        data = await fmp_client.get_etf_holder(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/etf/info/{symbol}")
async def get_etf_info(
    symbol: str = Path(..., description="ETF ticker symbol")
):
    """
    Get ETF information including expense ratio, inception date, and strategy.
    """
    try:
        data = await fmp_client.get_etf_info(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Economic Data ====================

@router.get("/economic/calendar")
async def get_economic_calendar(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get economic calendar with upcoming economic indicators and events.
    """
    try:
        data = await fmp_client.get_economic_calendar(from_date, to_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Search & Lists ====================

@router.get("/search/company")
async def search_company(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum results"),
    exchange: Optional[str] = Query(None, description="Filter by exchange")
):
    """
    Search for companies by name or ticker symbol.
    """
    try:
        data = await fmp_client.search_company(query, limit, exchange)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/ticker")
async def search_ticker(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Maximum results"),
    exchange: Optional[str] = Query(None, description="Filter by exchange")
):
    """
    Search for ticker symbols.
    """
    try:
        data = await fmp_client.search_ticker(query, limit, exchange)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/stocks")
async def get_all_stocks():
    """
    Get list of all available stock symbols.
    """
    try:
        data = await fmp_client.get_symbols_list()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/etfs")
async def get_all_etfs():
    """
    Get list of all available ETF symbols.
    """
    try:
        data = await fmp_client.get_etf_list()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list/indexes")
async def get_available_indexes():
    """
    Get list of all available market indexes.
    """
    try:
        data = await fmp_client.get_available_indexes()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
