"""Real-time data service — hybrid DB → API → scrape fallback chain.

Resolution order for any data request:
1. Redis cache (seconds-level for quotes, hours for fundamentals)
2. PostgreSQL (if data exists and is fresh enough)
3. External APIs (Upstox/Kite for live quotes, FMP for fundamentals)
4. Web scraping (NSE/BSE/MoneyControl/Screener.in)
5. Company IR page crawl (last resort)

All fetched data is persisted back to Postgres and cached in Redis so
subsequent requests are served instantly.
"""

import logging
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from src.db.database import SessionLocal
from src.db.models import Company, FinancialRatio, FinancialStatementRaw
from src.services.cache_service import CacheService, CacheTTL
from src.services.web_scraper import CompanyWebScraper

logger = logging.getLogger(__name__)


class RealTimeDataService:
    """Provides real-time financial data with multi-layer fallback."""

    STALE_QUOTE_HOURS = 0.5
    STALE_FINANCIALS_DAYS = 30

    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._own_session = db is None
        self.cache = CacheService()
        self.scraper = CompanyWebScraper()

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def close(self):
        self.scraper.close()
        if self._own_session and self._db is not None:
            self._db.close()
            self._db = None

    # -------------------------------------------------------------- #
    #  Quote (real-time price)                                         #
    # -------------------------------------------------------------- #

    async def get_quote(self, company_id: UUID) -> Dict[str, Any]:
        """Get the latest price quote for a company."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"error": "Company not found"}

        cache_key = str(company_id)
        cached = self.cache.get("quote", cache_key)
        if cached:
            return cached

        result = await self._fetch_quote_from_api(company)
        if not result:
            result = self._fetch_quote_from_scraper(company)
        if not result:
            result = {"company_id": str(company_id), "name": company.name, "quote": None, "message": "No live data available"}

        result["company_id"] = str(company_id)
        result["name"] = company.name
        self.cache.set("quote", cache_key, result, CacheTTL.QUOTE_LTP)
        return result

    async def _fetch_quote_from_api(self, company: Company) -> Optional[Dict[str, Any]]:
        """Try broker APIs: Upstox first, then Kite, then FMP."""
        if company.isin:
            try:
                from src.external_apis.Upstox_api.client import UpstoxClient
                client = UpstoxClient()
                if client.access_token:
                    nse_key = f"NSE_EQ|{company.isin}"
                    data = await client.get_ltp_quote([nse_key])
                    if data and data.get("data"):
                        quote_data = list(data["data"].values())[0] if isinstance(data["data"], dict) else data["data"]
                        return {
                            "source": "Upstox",
                            "last_price": quote_data.get("last_price", quote_data.get("ltp")),
                            "instrument_key": nse_key,
                            "fetched_at": datetime.utcnow().isoformat(),
                        }
            except Exception as e:
                logger.debug("Upstox quote failed for %s: %s", company.isin, e)

        kite_ticker = company.ticker_nse or company.ticker_bse
        if kite_ticker:
            try:
                from src.external_apis.Kite_api.client import KiteClient
                client = KiteClient()
                exchange = "NSE" if company.ticker_nse else "BSE"
                instruments = [f"{exchange}:{kite_ticker}"]
                data = await client.get_ltp(instruments)
                if data:
                    quote_data = list(data.values())[0] if isinstance(data, dict) else data
                    return {
                        "source": "Kite",
                        "last_price": quote_data.get("last_price", quote_data.get("ltp")),
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.debug("Kite quote failed for %s: %s", kite_ticker, e)

        fmp_ticker = company.ticker_nse or company.ticker_bse
        if fmp_ticker:
            try:
                from src.external_apis.FMP_api.client import FMPClient
                client = FMPClient()
                suffix = ".NS" if company.ticker_nse else ".BO"
                fmp_symbol = f"{fmp_ticker}{suffix}"
                data = await client.get_quote(fmp_symbol)
                if data and isinstance(data, list) and data[0]:
                    item = data[0]
                    return {
                        "source": "FMP",
                        "last_price": item.get("price"),
                        "change": item.get("change"),
                        "change_pct": item.get("changesPercentage"),
                        "volume": item.get("volume"),
                        "market_cap": item.get("marketCap"),
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.debug("FMP quote failed for %s: %s", fmp_ticker, e)

        return None

    def _fetch_quote_from_scraper(self, company: Company) -> Optional[Dict[str, Any]]:
        """Fall back to web scraping for price data."""
        data = self.scraper.get_company_overview(
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
            isin=company.isin,
        )
        if data and data.get("last_price"):
            return {
                "source": data.get("source", "web"),
                "last_price": data["last_price"],
                "change": data.get("change"),
                "change_pct": data.get("change_pct"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "volume": data.get("volume"),
                "fetched_at": data.get("fetched_at", datetime.utcnow().isoformat()),
            }
        return None

    # -------------------------------------------------------------- #
    #  Financials (statements & ratios)                                #
    # -------------------------------------------------------------- #

    def get_financials(
        self,
        company_id: UUID,
        periods: int = 4,
    ) -> Dict[str, Any]:
        """Get financial statements — DB first, then API/scrape fallback."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"error": "Company not found", "company_id": str(company_id)}

        cache_key = f"{company_id}:{periods}"
        cached = self.cache.get("financials", cache_key)
        if cached:
            return cached

        db_data = self._get_financials_from_db(company, periods)
        if db_data and db_data.get("periods"):
            self.cache.set("financials", cache_key, db_data, CacheTTL.FINANCIALS)
            return db_data

        fmp_data = self._fetch_financials_from_fmp(company)
        if fmp_data and fmp_data.get("periods"):
            self._persist_fmp_financials(company, fmp_data)
            self.cache.set("financials", cache_key, fmp_data, CacheTTL.FINANCIALS)
            return fmp_data

        scraped = self._fetch_financials_fallback(company)
        if scraped:
            self._persist_scraped_financials(company, scraped)
            db_data = self._get_financials_from_db(company, periods)
            if db_data and db_data.get("periods"):
                self.cache.set("financials", cache_key, db_data, CacheTTL.FINANCIALS)
                return db_data

            result = {
                "company_id": str(company_id),
                "company_name": company.name,
                "source": scraped.get("source", "web"),
                "raw_data": scraped,
            }
            self.cache.set("financials", cache_key, result, CacheTTL.SCRAPED_DATA)
            return result

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "periods": [],
            "message": "No financial data available. Data will be populated on next sync.",
        }

    def _get_financials_from_db(self, company: Company, periods: int) -> Dict[str, Any]:
        stmts = (
            self.db.query(FinancialStatementRaw)
            .filter(FinancialStatementRaw.company_id == company.id)
            .order_by(FinancialStatementRaw.period_end.desc())
            .limit(periods * 50)
            .all()
        )

        periods_data: Dict[date, List[Dict]] = {}
        seen_periods: set = set()
        for stmt in stmts:
            if len(seen_periods) >= periods and stmt.period_end not in seen_periods:
                continue
            seen_periods.add(stmt.period_end)
            if stmt.period_end not in periods_data:
                periods_data[stmt.period_end] = []
            periods_data[stmt.period_end].append({
                "line_item": stmt.line_item,
                "value": float(stmt.value) if stmt.value else None,
                "unit": stmt.unit,
                "statement_type": stmt.statement_type,
            })

        sorted_periods = sorted(periods_data.keys(), reverse=True)[:periods]
        latest_period = sorted_periods[0] if sorted_periods else None

        return {
            "company_id": str(company.id),
            "company_name": company.name,
            "latest_period": latest_period.isoformat() if latest_period else None,
            "periods": [
                {"period_end": p.isoformat(), "items": periods_data[p]}
                for p in sorted_periods
            ],
        }

    def _fetch_financials_fallback(self, company: Company) -> Optional[Dict[str, Any]]:
        """Try scraping financial data from web sources."""
        return self.scraper.get_financial_results(
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
        )

    def _persist_scraped_financials(self, company: Company, scraped: Dict[str, Any]) -> None:
        """Best-effort persist scraped financial data into FinancialStatementRaw."""
        try:
            if scraped.get("data"):
                columns = scraped.get("columns", [])
                for label, values in scraped["data"].items():
                    for i, val in enumerate(values):
                        if val is None:
                            continue
                        period_label = columns[i] if i < len(columns) else ""
                        period_end = self._parse_period_label(period_label)
                        if not period_end:
                            continue

                        existing = (
                            self.db.query(FinancialStatementRaw)
                            .filter(
                                FinancialStatementRaw.company_id == company.id,
                                FinancialStatementRaw.line_item == label,
                                FinancialStatementRaw.period_end == period_end,
                            )
                            .first()
                        )
                        if existing:
                            continue

                        stmt = FinancialStatementRaw(
                            company_id=company.id,
                            statement_type=self._guess_statement_type(label),
                            period_start=period_end.replace(day=1),
                            period_end=period_end,
                            fiscal_year=period_end.year,
                            quarter=self._guess_quarter(period_end),
                            line_item=label,
                            value=Decimal(str(val)),
                            currency="INR",
                            unit="Cr",
                        )
                        self.db.add(stmt)
                self.db.commit()
            elif scraped.get("periods"):
                for period_data in scraped["periods"]:
                    period_str = period_data.get("period", "")
                    period_end = self._parse_period_label(period_str)
                    if not period_end:
                        continue
                    for key in ("revenue", "net_profit", "eps"):
                        val = period_data.get(key)
                        if val is None:
                            continue
                        existing = (
                            self.db.query(FinancialStatementRaw)
                            .filter(
                                FinancialStatementRaw.company_id == company.id,
                                FinancialStatementRaw.line_item == key,
                                FinancialStatementRaw.period_end == period_end,
                            )
                            .first()
                        )
                        if existing:
                            continue
                        stmt = FinancialStatementRaw(
                            company_id=company.id,
                            statement_type="income_statement",
                            period_start=period_end.replace(day=1),
                            period_end=period_end,
                            fiscal_year=period_end.year,
                            line_item=key,
                            value=Decimal(str(val)),
                            currency="INR",
                            unit="Cr",
                        )
                        self.db.add(stmt)
                self.db.commit()
        except Exception as e:
            logger.warning("Failed to persist scraped financials for %s: %s", company.name, e)
            self.db.rollback()

    # -------------------------------------------------------------- #
    #  Ratios                                                          #
    # -------------------------------------------------------------- #

    def get_ratios(
        self,
        company_id: UUID,
        period: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get financial ratios — DB first, then scrape fallback."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"error": "Company not found"}

        cache_key = f"{company_id}:{period.isoformat() if period else 'latest'}"
        cached = self.cache.get("ratios", cache_key)
        if cached:
            return cached

        query = self.db.query(FinancialRatio).filter(FinancialRatio.company_id == company_id)
        if period:
            query = query.filter(FinancialRatio.period_end == period)
        ratio = query.order_by(FinancialRatio.period_end.desc()).first()

        if ratio:
            result = {
                "company_id": str(company_id),
                "company_name": company.name,
                "period_end": ratio.period_end.isoformat(),
                "fiscal_year": ratio.fiscal_year,
                "quarter": ratio.quarter,
                "ratios": {
                    "roe": float(ratio.roe) if ratio.roe else None,
                    "roce": float(ratio.roce) if ratio.roce else None,
                    "gross_margin": float(ratio.gross_margin) if ratio.gross_margin else None,
                    "ebitda_margin": float(ratio.ebitda_margin) if ratio.ebitda_margin else None,
                    "net_margin": float(ratio.net_margin) if ratio.net_margin else None,
                    "debt_to_equity": float(ratio.debt_to_equity) if ratio.debt_to_equity else None,
                    "interest_coverage": float(ratio.interest_coverage) if ratio.interest_coverage else None,
                    "current_ratio": float(ratio.current_ratio) if ratio.current_ratio else None,
                    "pe_ratio": float(ratio.pe_ratio) if ratio.pe_ratio else None,
                    "pb_ratio": float(ratio.pb_ratio) if ratio.pb_ratio else None,
                    "revenue_growth_yoy": float(ratio.revenue_growth_yoy) if ratio.revenue_growth_yoy else None,
                    "pat_growth_yoy": float(ratio.pat_growth_yoy) if ratio.pat_growth_yoy else None,
                    "eps_growth_yoy": float(ratio.eps_growth_yoy) if ratio.eps_growth_yoy else None,
                },
            }
            self.cache.set("ratios", cache_key, result, CacheTTL.RATIOS)
            return result

        fmp_ratios = self._fetch_ratios_from_fmp(company)
        if fmp_ratios and fmp_ratios.get("ratios"):
            self.cache.set("ratios", cache_key, fmp_ratios, CacheTTL.RATIOS)
            return fmp_ratios

        scraped = self.scraper.get_company_overview(
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
            isin=company.isin,
        )
        if scraped:
            ratios = {}
            for key in ("pe_ratio", "pb_ratio", "roe", "roce", "debt_to_equity", "dividend_yield"):
                if scraped.get(key) is not None:
                    ratios[key] = scraped[key]

            if ratios:
                result = {
                    "company_id": str(company_id),
                    "company_name": company.name,
                    "source": scraped.get("source", "web"),
                    "ratios": ratios,
                }
                self.cache.set("ratios", cache_key, result, CacheTTL.SCRAPED_DATA)
                return result

        return {
            "company_id": str(company_id),
            "company_name": company.name,
            "ratios": {},
            "message": "No ratio data available",
        }

    # -------------------------------------------------------------- #
    #  Company profile enrichment                                      #
    # -------------------------------------------------------------- #

    def enrich_company(self, company_id: UUID) -> Dict[str, Any]:
        """Fill in missing company fields from web sources."""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return {"error": "Company not found"}

        scraped = self.scraper.get_company_overview(
            ticker_nse=company.ticker_nse,
            ticker_bse=company.ticker_bse,
            isin=company.isin,
        )
        if not scraped:
            return {"company_id": str(company_id), "enriched": False}

        updated_fields = []
        if scraped.get("sector") and not company.sector:
            company.sector = scraped["sector"]
            updated_fields.append("sector")
        if scraped.get("industry") and not company.industry:
            company.industry = scraped["industry"]
            updated_fields.append("industry")
        if scraped.get("name") and (not company.legal_name or company.legal_name == company.name):
            company.legal_name = scraped["name"]
            updated_fields.append("legal_name")
        if scraped.get("market_cap") and not company.market_cap_inr:
            mc = scraped["market_cap"]
            if isinstance(mc, (int, float)):
                company.market_cap_inr = int(mc)
                updated_fields.append("market_cap_inr")

        if updated_fields:
            company.updated_at = datetime.utcnow()
            self.db.commit()

        return {
            "company_id": str(company_id),
            "enriched": bool(updated_fields),
            "updated_fields": updated_fields,
            "source": scraped.get("source"),
        }

    # -------------------------------------------------------------- #
    #  Search / lookup                                                 #
    # -------------------------------------------------------------- #

    def find_company(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search the local company universe by name or ticker."""
        q = query.strip().upper()
        companies = (
            self.db.query(Company)
            .filter(
                Company.listing_status == "active",
                (
                    Company.ticker_nse.ilike(f"%{q}%")
                    | Company.ticker_bse.ilike(f"%{q}%")
                    | Company.name.ilike(f"%{query}%")
                    | Company.isin.ilike(f"%{q}%")
                ),
            )
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(c.id),
                "name": c.name,
                "ticker_nse": c.ticker_nse,
                "ticker_bse": c.ticker_bse,
                "isin": c.isin,
                "sector": c.sector,
            }
            for c in companies
        ]

    # -------------------------------------------------------------- #
    #  FMP API fallback                                                #
    # -------------------------------------------------------------- #

    @staticmethod
    def _get_fmp_symbol(company: Company) -> Optional[str]:
        """Build FMP-compatible symbol (e.g. RENUKA.NS for Indian stocks)."""
        if company.ticker_nse:
            return f"{company.ticker_nse}.NS"
        if company.ticker_bse:
            return f"{company.ticker_bse}.BO"
        return None

    def _fetch_financials_from_fmp(self, company: Company) -> Optional[Dict[str, Any]]:
        """Fetch income-statement data from FMP API as a fallback.

        Uses sync httpx so it can be called from the synchronous
        ``get_financials`` code path without async bridging.
        """
        symbol = self._get_fmp_symbol(company)
        if not symbol:
            return None

        api_key = os.getenv("FMP_API_KEY", "")
        if not api_key:
            return None

        base = "https://financialmodelingprep.com/api/v3"

        fmp_fields = [
            ("revenue", "revenue"),
            ("costOfRevenue", "cost_of_revenue"),
            ("grossProfit", "gross_profit"),
            ("operatingIncome", "operating_income"),
            ("operatingExpenses", "operating_expenses"),
            ("interestExpense", "interest_expense"),
            ("depreciationAndAmortization", "depreciation"),
            ("ebitda", "ebitda"),
            ("incomeBeforeTax", "profit_before_tax"),
            ("incomeTaxExpense", "tax_expense"),
            ("netIncome", "net_profit"),
            ("eps", "eps"),
            ("epsdiluted", "eps_diluted"),
        ]
        eps_fields = {"eps", "eps_diluted"}

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(
                    f"{base}/income-statement/{symbol}",
                    params={"period": "quarter", "limit": 8, "apikey": api_key},
                )
                if resp.status_code != 200:
                    return None
                income_data = resp.json()
                if not income_data or not isinstance(income_data, list):
                    return None

                currency = income_data[0].get("reportedCurrency", "INR")
                is_inr = currency == "INR"
                divisor = 1e7 if is_inr else 1
                unit = "Cr" if is_inr else currency

                periods: List[Dict[str, Any]] = []
                for stmt in income_data:
                    items: List[Dict[str, Any]] = []
                    for fmp_key, local_key in fmp_fields:
                        val = stmt.get(fmp_key)
                        if val is None:
                            continue
                        if local_key in eps_fields:
                            items.append({
                                "line_item": local_key,
                                "value": val,
                                "unit": currency,
                                "statement_type": "income_statement",
                            })
                        else:
                            items.append({
                                "line_item": local_key,
                                "value": round(val / divisor, 2),
                                "unit": unit,
                                "statement_type": "income_statement",
                            })
                    if items:
                        periods.append({
                            "period_end": stmt.get("date", ""),
                            "items": items,
                        })

                if not periods:
                    return None

                return {
                    "company_id": str(company.id),
                    "company_name": company.name,
                    "source": "FMP",
                    "latest_period": periods[0]["period_end"],
                    "periods": periods,
                }
        except Exception as e:
            logger.debug("FMP financials fetch failed for %s: %s", symbol, e)
            return None

    def _fetch_ratios_from_fmp(self, company: Company) -> Optional[Dict[str, Any]]:
        """Fetch ratios + key-metrics from FMP API as a fallback."""
        symbol = self._get_fmp_symbol(company)
        if not symbol:
            return None

        api_key = os.getenv("FMP_API_KEY", "")
        if not api_key:
            return None

        base = "https://financialmodelingprep.com/api/v3"

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(
                    f"{base}/ratios/{symbol}",
                    params={"period": "quarter", "limit": 1, "apikey": api_key},
                )
                ratio_data = resp.json() if resp.status_code == 200 else []
                if not isinstance(ratio_data, list):
                    ratio_data = []

                resp2 = client.get(
                    f"{base}/key-metrics/{symbol}",
                    params={"period": "quarter", "limit": 1, "apikey": api_key},
                )
                metric_data = resp2.json() if resp2.status_code == 200 else []
                if not isinstance(metric_data, list):
                    metric_data = []

            if not ratio_data and not metric_data:
                return None

            ratios: Dict[str, Any] = {}
            if ratio_data:
                r = ratio_data[0]
                ratios.update({
                    "roe": r.get("returnOnEquity"),
                    "roce": r.get("returnOnCapitalEmployed"),
                    "gross_margin": r.get("grossProfitMargin"),
                    "ebitda_margin": r.get("ebitdaPerRevenue"),
                    "net_margin": r.get("netIncomePerRevenue"),
                    "debt_to_equity": r.get("debtEquityRatio"),
                    "interest_coverage": r.get("interestCoverage"),
                    "current_ratio": r.get("currentRatio"),
                    "pe_ratio": r.get("priceEarningsRatio"),
                    "pb_ratio": r.get("priceToBookRatio"),
                })

            if metric_data:
                m = metric_data[0]
                ratios.setdefault("pe_ratio", m.get("peRatio"))
                ratios.setdefault("pb_ratio", m.get("pbRatio"))
                ratios.setdefault("dividend_yield", m.get("dividendYield"))
                ratios.setdefault("earnings_yield", m.get("earningsYield"))

            ratios = {k: v for k, v in ratios.items() if v is not None}
            if not ratios:
                return None

            period_end = None
            if ratio_data:
                period_end = ratio_data[0].get("date")
            elif metric_data:
                period_end = metric_data[0].get("date")

            return {
                "company_id": str(company.id),
                "company_name": company.name,
                "source": "FMP",
                "period_end": period_end,
                "ratios": ratios,
            }
        except Exception as e:
            logger.debug("FMP ratios fetch failed for %s: %s", symbol, e)
            return None

    def _persist_fmp_financials(
        self, company: Company, fmp_data: Dict[str, Any]
    ) -> None:
        """Best-effort persist FMP financial data into FinancialStatementRaw."""
        try:
            for period_data in fmp_data.get("periods", []):
                period_end_str = period_data.get("period_end", "")
                if not period_end_str:
                    continue
                period_end = date.fromisoformat(period_end_str)

                for item in period_data.get("items", []):
                    val = item.get("value")
                    if val is None:
                        continue
                    existing = (
                        self.db.query(FinancialStatementRaw)
                        .filter(
                            FinancialStatementRaw.company_id == company.id,
                            FinancialStatementRaw.line_item == item["line_item"],
                            FinancialStatementRaw.period_end == period_end,
                        )
                        .first()
                    )
                    if existing:
                        continue
                    stmt = FinancialStatementRaw(
                        company_id=company.id,
                        statement_type=item.get("statement_type", "income_statement"),
                        period_start=period_end.replace(day=1),
                        period_end=period_end,
                        fiscal_year=period_end.year,
                        quarter=self._guess_quarter(period_end),
                        line_item=item["line_item"],
                        value=Decimal(str(val)),
                        currency="INR",
                        unit=item.get("unit", "Cr"),
                    )
                    self.db.add(stmt)
            self.db.commit()
        except Exception as e:
            logger.warning(
                "Failed to persist FMP financials for %s: %s", company.name, e
            )
            self.db.rollback()

    # -------------------------------------------------------------- #
    #  Helpers                                                         #
    # -------------------------------------------------------------- #

    @staticmethod
    def _parse_period_label(label: str) -> Optional[date]:
        """Best-effort parse a period label like 'Mar 2024', 'Jun 2023', 'Q3 FY24'."""
        import re

        label = label.strip()
        if not label:
            return None

        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        m = re.match(r"(\w{3})\s+(\d{4})", label, re.I)
        if m:
            month_name = m.group(1).lower()
            year = int(m.group(2))
            month = month_map.get(month_name)
            if month:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return date(year, month, last_day)

        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", label)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

        return None

    @staticmethod
    def _guess_statement_type(label: str) -> str:
        label_lower = label.lower()
        if any(kw in label_lower for kw in ("revenue", "sales", "income", "profit", "eps", "tax", "expense")):
            return "income_statement"
        if any(kw in label_lower for kw in ("asset", "liability", "equity", "debt", "capital", "reserve")):
            return "balance_sheet"
        if any(kw in label_lower for kw in ("cash", "capex", "investing", "financing")):
            return "cash_flow"
        return "other"

    @staticmethod
    def _guess_quarter(d: date) -> Optional[int]:
        return (d.month - 1) // 3 + 1
