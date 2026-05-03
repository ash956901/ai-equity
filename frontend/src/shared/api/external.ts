import {
  type AICompany,
  type EnrichedNewsItem,
  type TimelineEvent,
  type CompanySearchResult,
  type NewsDataResponse,
  type SecFiling,
  type SentimentFeedResponse,
} from "../types/api";
import { aiGet, getJson } from "./core";

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
  _expertiseLevel = "intermediate"
): Promise<EnrichedNewsItem[]> {
  const normalizedLimit = Math.min(Math.max(limit, 1), 50);
  const params = new URLSearchParams();
  params.set("limit", String(normalizedLimit));
  if (query && query.trim() !== "") {
    params.set("query", query.trim());
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
  try {
    const payload = await getJson<{ count?: number }>(
      "/portfolios/me/holdings-count",
    );
    return typeof payload?.count === "number" ? payload.count : 0;
  } catch {
    return 0;
  }
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
