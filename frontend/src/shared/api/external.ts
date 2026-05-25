import {
  type AICompany,
  type EnrichedNewsItem,
  type TimelineEvent,
  type CompanySearchResult,
  type NewsDataResponse,
  type SecFiling,
  type SentimentFeedResponse,
  type UpstoxHolding,
} from "../types/api";
import { aiGet, aiPost, getJson } from "./core";

interface UpstoxHoldingsResponse {
  data?: UpstoxHolding[];
}

function mapEnrichedToArticle(item: EnrichedNewsItem, index: number) {
  return {
    article_id: `${item.source}-${item.published_at}-${index}`,
    title: item.title,
    description: item.summary,
    source_name: item.source,
    pubDate: item.published_at,
    link: item.url ?? undefined,
  };
}

export async function fetchNewsRadar(
  limit = 20,
  query?: string,
  _expertiseLevel = "intermediate",
  forceRefresh = false
): Promise<EnrichedNewsItem[]> {
  const normalizedLimit = Math.min(Math.max(limit, 1), 50);
  const params = new URLSearchParams();
  params.set("limit", String(normalizedLimit));
  if (query && query.trim() !== "") {
    params.set("query", query.trim());
  }
  if (forceRefresh) {
    params.set("force_refresh", "true");
  }

  return aiGet<EnrichedNewsItem[]>(`/get-news?${params.toString()}`, 90000);
}

export async function fetchMarketHeadlines(limit = 20, symbolOrName?: string): Promise<NewsDataResponse> {
  const normalizedLimit = Math.min(Math.max(limit, 1), 50);
  const params = new URLSearchParams();
  params.set("limit", String(normalizedLimit));
  const query = symbolOrName?.trim();
  if (query) {
    params.set("query", query);
  }
  let feed = await aiGet<EnrichedNewsItem[]>(`/get-news?${params.toString()}`, 90000);

  if (query && feed.length === 0) {
    feed = await aiGet<EnrichedNewsItem[]>(`/get-news?limit=${normalizedLimit}`, 90000);
  }

  const results = feed.slice(0, normalizedLimit).map(mapEnrichedToArticle);

  return {
    status: "success",
    totalResults: results.length,
    results,
  };
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
  const normalizedSymbol = symbol.trim().toUpperCase();
  const query = symbol.trim();
  const cappedSize = Math.max(1, size);
  const normalizedHoursBack = Math.max(1, Math.min(hoursBack, 72));
  const requested = Math.min(Math.max(cappedSize * Math.ceil(normalizedHoursBack / 8), 12), 36);
  const params = new URLSearchParams();
  params.set("limit", String(requested));
  if (query) {
    params.set("query", query);
  }

  let feed: EnrichedNewsItem[] = [];
  try {
    feed = await aiGet<EnrichedNewsItem[]>(`/get-news?${params.toString()}`, 90000);
  } catch {
    feed = await aiGet<EnrichedNewsItem[]>(`/get-news?limit=${requested}`, 90000);
  }

  if (query && feed.length === 0) {
    feed = await aiGet<EnrichedNewsItem[]>(`/get-news?limit=${requested}`, 90000);
  }

  const selected = feed.slice(0, cappedSize);

  return {
    symbol: normalizedSymbol,
    total_results: selected.length,
    articles: selected.map((item, index) => ({
      ...mapEnrichedToArticle(item, index),
      sentiment: item.sentiment,
    })),
  };
}

interface FilingRecord {
  id: string;
  filing_type?: string;
  title?: string;
  filing_date?: string;
  source_url?: string;
  status?: string;
  period_start?: string;
  period_end?: string;
}

async function resolveCompanyId(symbol: string): Promise<string | null> {
  const normalized = symbol.trim().toUpperCase();
  const params = new URLSearchParams({ q: normalized, limit: "10" });
  const companies = await aiGet<AICompany[]>(`/companies/search?${params.toString()}`);
  const company =
    companies.find((c) => c.ticker_nse?.toUpperCase() === normalized) ||
    companies.find((c) => c.ticker_bse?.toUpperCase() === normalized) ||
    companies[0];
  return company?.id ?? null;
}

export async function fetchSecFilings(
  symbol: string,
  limit = 12,
  filingType?: string
): Promise<SecFiling[]> {
  const normalized = symbol.trim().toUpperCase();
  if (!normalized) return [];

  const companyId = await resolveCompanyId(normalized);
  if (!companyId) return [];

  const params = new URLSearchParams({ limit: String(limit) });
  if (filingType) params.set("filing_type", filingType);

  const filings = await aiGet<FilingRecord[]>(
    `/companies/${companyId}/filings?${params.toString()}`
  );

  return filings.map((f) => ({
    symbol: normalized,
    title: f.title,
    filingDate: f.filing_date,
    acceptedDate: f.filing_date,
    type: f.filing_type,
    url: f.source_url,
    finalLink: f.source_url,
  }));
}

export async function syncCompanyFilings(
  symbol: string
): Promise<{ status: string; company_name?: string; sources?: string[] }> {
  const normalized = symbol.trim().toUpperCase();
  if (!normalized) return { status: "error" };

  const companyId = await resolveCompanyId(normalized);
  if (!companyId) return { status: "not_found" };

  return aiPost<{ status: string; company_name?: string; sources?: string[] }>(
    `/companies/${companyId}/filings/sync`,
    {}
  );
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
