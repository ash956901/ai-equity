import {
  type CompanySearchResult,
  type NewsDataResponse,
  type SecFiling,
  type SentimentFeedResponse,
  type UpstoxHolding,
} from "../types/api";
import { getJson } from "./core";

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
  const normalized = encodeURIComponent(symbol.toUpperCase());
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (filingType) {
    params.set("filing_type", filingType);
  }
  return getJson<SecFiling[]>(`/fmp/sec/filings/${normalized}?${params.toString()}`);
}

export async function searchCompanies(
  query: string,
  limit = 6
): Promise<CompanySearchResult[]> {
  const params = new URLSearchParams();
  params.set("query", query);
  params.set("limit", String(limit));
  return getJson<CompanySearchResult[]>(`/fmp/search/company?${params.toString()}`);
}
