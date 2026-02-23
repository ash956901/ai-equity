"""
FastAPI routes for FRED (Federal Reserve Economic Data) API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, List
from datetime import datetime, date, timedelta

from .client import FREDClient
from .models import *

router = APIRouter(prefix="/fred", tags=["FRED Economic Data API"])

# Initialize FRED client
fred_client = FREDClient()


# ==================== Core Series Endpoints ====================

@router.get("/series/{series_id}")
async def get_series_data(
    series_id: str = Path(..., description="FRED series ID (e.g., GDP, UNRATE, DGS10)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(None, description="Maximum number of observations"),
    sort_order: str = Query("asc", description="Sort order: asc or desc")
):
    """
    Get observations for any FRED economic data series.
    
    **Popular Series IDs:**
    - GDP: Real Gross Domestic Product
    - UNRATE: Unemployment Rate
    - CPIAUCSL: Consumer Price Index
    - FEDFUNDS: Federal Funds Rate
    - DGS10: 10-Year Treasury Rate
    """
    try:
        data = await fred_client.get_series(
            series_id=series_id.upper(),
            observation_start=start_date,
            observation_end=end_date,
            limit=limit,
            sort_order=sort_order
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/info")
async def get_series_metadata(
    series_id: str = Path(..., description="FRED series ID")
):
    """
    Get metadata information about a FRED series including title, units, frequency, and notes.
    """
    try:
        data = await fred_client.get_series_info(series_id.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_series(
    query: str = Query(..., description="Search keywords"),
    limit: int = Query(100, description="Maximum results", ge=1, le=1000),
    order_by: str = Query("popularity", description="Order by: search_rank, popularity, series_id, title")
):
    """
    Search for economic data series by keywords.
    
    **Example queries:**
    - "inflation"
    - "unemployment rate"
    - "GDP growth"
    - "interest rate"
    """
    try:
        data = await fred_client.search_series(query, limit, order_by)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Interest Rates ====================

@router.get("/rates/interest")
async def get_interest_rates(
    rate_type: str = Query("fed_funds", description="Rate type: fed_funds, treasury_10y, treasury_2y, treasury_3m, treasury_5y, treasury_30y"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get interest rate data from Federal Reserve.
    
    **Available Rate Types:**
    - fed_funds: Federal Funds Effective Rate
    - treasury_10y: 10-Year Treasury Constant Maturity Rate
    - treasury_2y: 2-Year Treasury Constant Maturity Rate
    - treasury_3m: 3-Month Treasury Bill Rate
    - treasury_5y: 5-Year Treasury Constant Maturity Rate
    - treasury_30y: 30-Year Treasury Constant Maturity Rate
    """
    try:
        data = await fred_client.get_interest_rates(rate_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rates/yield-curve")
async def get_yield_curve(
    date: Optional[str] = Query(None, description="Specific date (YYYY-MM-DD), leave empty for latest")
):
    """
    Get Treasury yield curve data across all maturities.
    
    Returns yields for: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
    """
    try:
        data = await fred_client.get_yield_curve(date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rates/credit-spreads")
async def get_credit_spreads(
    spread_type: str = Query("high_yield", description="Spread type: high_yield, investment_grade, baa_aaa"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get corporate credit spread data.
    
    **Spread Types:**
    - high_yield: High Yield Corporate Bond Spread
    - investment_grade: Investment Grade Corporate Bond Spread
    - baa_aaa: BAA-AAA Corporate Bond Spread
    """
    try:
        data = await fred_client.get_credit_spreads(spread_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Inflation ====================

@router.get("/inflation")
async def get_inflation_data(
    inflation_type: str = Query("cpi", description="Inflation measure: cpi, core_cpi, pce, core_pce, ppi"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get inflation data from various measures.
    
    **Inflation Types:**
    - cpi: Consumer Price Index for All Urban Consumers
    - core_cpi: CPI excluding food and energy
    - pce: Personal Consumption Expenditures Price Index
    - core_pce: Core PCE (Fed's preferred inflation measure)
    - ppi: Producer Price Index
    """
    try:
        data = await fred_client.get_inflation(inflation_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GDP & Growth ====================

@router.get("/gdp")
async def get_gdp_data(
    gdp_type: str = Query("real_gdp", description="GDP measure: real_gdp, nominal_gdp, gdp_growth, gdp_per_capita"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get Gross Domestic Product data.
    
    **GDP Types:**
    - real_gdp: Real GDP (inflation-adjusted)
    - nominal_gdp: Nominal GDP
    - gdp_growth: Real GDP Growth Rate (%)
    - gdp_per_capita: Real GDP per Capita
    """
    try:
        data = await fred_client.get_gdp(gdp_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Labor Market ====================

@router.get("/unemployment")
async def get_unemployment_data(
    unemployment_type: str = Query("rate", description="Unemployment measure: rate, level, initial_claims, continuing_claims"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get unemployment and labor market data.
    
    **Unemployment Types:**
    - rate: Unemployment Rate (%)
    - level: Unemployment Level (thousands)
    - initial_claims: Initial Jobless Claims (weekly)
    - continuing_claims: Continuing Jobless Claims
    """
    try:
        data = await fred_client.get_unemployment(unemployment_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Money Supply ====================

@router.get("/money-supply")
async def get_money_supply_data(
    supply_type: str = Query("m2", description="Money supply measure: m1, m2, m3"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get money supply data.
    
    **Supply Types:**
    - m1: M1 Money Supply (currency + demand deposits)
    - m2: M2 Money Supply (M1 + savings deposits)
    - m3: M3 Money Supply (broad money)
    """
    try:
        data = await fred_client.get_money_supply(supply_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Consumer Sentiment ====================

@router.get("/sentiment/consumer")
async def get_consumer_sentiment_data(
    sentiment_type: str = Query("umich", description="Sentiment measure: umich, consumer_confidence"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get consumer sentiment data.
    
    **Sentiment Types:**
    - umich: University of Michigan Consumer Sentiment Index
    - consumer_confidence: Consumer Confidence Index
    """
    try:
        data = await fred_client.get_consumer_sentiment(sentiment_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Industrial Production ====================

@router.get("/industrial-production")
async def get_industrial_production_data(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get Industrial Production Index data.
    
    Measures real output of manufacturing, mining, and electric/gas utilities.
    """
    try:
        data = await fred_client.get_industrial_production(start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Housing Market ====================

@router.get("/housing")
async def get_housing_data(
    housing_type: str = Query("starts", description="Housing measure: starts, permits, sales, case_shiller, mortgage_rate"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get housing market data.
    
    **Housing Types:**
    - starts: Housing Starts (thousands of units)
    - permits: Building Permits
    - sales: New Home Sales
    - case_shiller: Case-Shiller Home Price Index
    - mortgage_rate: 30-Year Fixed Rate Mortgage Average
    """
    try:
        data = await fred_client.get_housing_data(housing_type, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Commodities ====================

@router.get("/commodities")
async def get_commodity_prices(
    commodity: str = Query("oil", description="Commodity: oil, gold, silver, copper, natural_gas"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get commodity price data.
    
    **Commodities:**
    - oil: Crude Oil Prices (WTI)
    - gold: Gold Fixing Price
    - silver: Silver Price
    - copper: Copper Price
    - natural_gas: Natural Gas Price
    """
    try:
        data = await fred_client.get_commodity_prices(commodity, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Exchange Rates ====================

@router.get("/exchange-rates")
async def get_exchange_rates(
    currency: str = Query("eur", description="Currency: eur, gbp, jpy, cny, cad"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Get foreign exchange rates (USD per foreign currency unit).
    
    **Currencies:**
    - eur: US Dollar to Euro
    - gbp: US Dollar to British Pound
    - jpy: US Dollar to Japanese Yen
    - cny: US Dollar to Chinese Yuan
    - cad: US Dollar to Canadian Dollar
    """
    try:
        data = await fred_client.get_exchange_rates(currency, start_date, end_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Categories ====================

@router.get("/categories/{category_id}")
async def get_category_info(
    category_id: int = Path(..., description="Category ID (0 for root)")
):
    """
    Get information about a FRED data category.
    """
    try:
        data = await fred_client.get_category(category_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category_id}/children")
async def get_category_children(
    category_id: int = Path(..., description="Parent category ID")
):
    """
    Get child categories of a FRED category.
    """
    try:
        data = await fred_client.get_category_children(category_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category_id}/series")
async def get_category_series(
    category_id: int = Path(..., description="Category ID"),
    limit: int = Query(100, description="Maximum results", ge=1, le=1000)
):
    """
    Get all series in a FRED category.
    """
    try:
        data = await fred_client.get_category_series(category_id, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Releases ====================

@router.get("/releases")
async def get_all_releases(
    limit: int = Query(100, description="Maximum results", ge=1, le=1000)
):
    """
    Get all FRED data releases.
    """
    try:
        data = await fred_client.get_releases(limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/releases/{release_id}")
async def get_release_info(
    release_id: int = Path(..., description="Release ID")
):
    """
    Get information about a specific FRED data release.
    """
    try:
        data = await fred_client.get_release_info(release_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/releases/{release_id}/series")
async def get_release_series(
    release_id: int = Path(..., description="Release ID"),
    limit: int = Query(100, description="Maximum results", ge=1, le=1000)
):
    """
    Get all series for a FRED release.
    """
    try:
        data = await fred_client.get_release_series(release_id, limit)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Tags ====================

@router.get("/series/{series_id}/tags")
async def get_series_tags(
    series_id: str = Path(..., description="FRED series ID")
):
    """
    Get tags associated with a FRED series.
    """
    try:
        data = await fred_client.get_series_tags(series_id.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/related")
async def get_related_tags(
    tag_names: str = Query(..., description="Semicolon-separated tag names")
):
    """
    Get tags related to specified tag names.
    """
    try:
        data = await fred_client.get_related_tags(tag_names)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
