import {
  type AICompany,
  type TimelineEvent,
  type CompanySearchResult,
  type NewsDataResponse,
  type SecFiling,
  type SentimentFeedResponse,
  type UpstoxHolding,
} from "../types/api";
import { aiGet, getJson } from "./core";

interface UpstoxHoldingsResponse {
  data?: UpstoxHolding[];
}

export async function fetchMarketHeadlines(): Promise<NewsDataResponse> {
  return getJson<NewsDataResponse>(
    "/newsdata/market/headlines?country=in&timeframe=6&size=6"
  );
}

export async function fetchHoldingsCount(): Promise<number> {
  const payload = await getJson<UpstoxHoldingsResponse | UpstoxHolding[]>(
    "/upstox/portfolio/holdings"
  );

  if (Array.isArray(payload)) {
    return payload.length;
  }

  return Array.isArray(payload.data) ? payload.data.length : 0;
}

export async function fetchTickerSentiment(
  symbol: string,
  hoursBack = 24,
  size = 8
): Promise<SentimentFeedResponse> {
  const normalized = encodeURIComponent(symbol.toUpperCase());
  return getJson<SentimentFeedResponse>(
    `/newsdata/sentiment/${normalized}?hours_back=${hoursBack}&size=${size}&language=en`
  );
}

export async function fetchSecFilings(
  symbol: string,
  limit = 12,
  filingType?: string
): Promise<SecFiling[]> {
  const normalized = symbol.trim().toUpperCase();
  if (!normalized) {
    return [];
  }

  const companyParams = new URLSearchParams();
  companyParams.set("q", normalized);
  companyParams.set("limit", "10");

  const companies = await aiGet<AICompany[]>(`/companies/search?${companyParams.toString()}`);
  const company =
    companies.find((item) => item.ticker_nse?.toUpperCase() === normalized) ||
    companies.find((item) => item.ticker_bse?.toUpperCase() === normalized) ||
    companies[0];

  if (!company?.id) {
    return [];
  }

  const params = new URLSearchParams();
  params.set("company_id", company.id);
  params.set("limit", String(Math.max(limit * 3, 30)));

  const timeline = await aiGet<TimelineEvent[]>(`/timeline/?${params.toString()}`);
  const filings = timeline
    .filter((event) => event.event_type === "filing")
    .map((event) => {
      const metadata = (event.metadata ?? {}) as {
        filing_type?: string;
        source_url?: string;
      };
      const filingDate = event.timestamp ? event.timestamp.slice(0, 10) : undefined;
      return {
        symbol: normalized,
        title: event.title,
        filingDate,
        acceptedDate: filingDate,
        type: metadata.filing_type,
        url: metadata.source_url,
        finalLink: metadata.source_url,
      } as SecFiling;
    })
    .filter((filing) => !filingType || filing.type === filingType)
    .slice(0, limit);

  return filings;
}

export async function searchCompanies(
  query: string,
  limit = 6
): Promise<CompanySearchResult[]> {
  const params = new URLSearchParams();
  params.set("q", query);
  params.set("limit", String(limit));
  const companies = await aiGet<AICompany[]>(`/companies/search?${params.toString()}`);
  return companies.map((company) => ({
    symbol: company.ticker_nse || company.ticker_bse,
    name: company.name,
    exchangeShortName: company.ticker_nse ? "NSE" : company.ticker_bse ? "BSE" : undefined,
    stockExchange: company.ticker_nse ? "National Stock Exchange" : company.ticker_bse ? "Bombay Stock Exchange" : undefined,
  }));
}
