export const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface HealthResponse {
  status?: string;
  message?: string;
}

export interface ApiStatusResponse {
  api_version?: string;
  status?: string;
}

export interface NewsDataArticle {
  article_id?: string;
  title?: string;
  description?: string;
  source_name?: string;
  pubDate?: string;
  link?: string;
}

export interface NewsDataResponse {
  status?: string;
  totalResults?: number;
  results?: NewsDataArticle[];
}

export interface UpstoxHolding {
  trading_symbol?: string;
  quantity?: number;
}

export interface SentimentFeedArticle {
  article_id?: string;
  title?: string;
  description?: string;
  source_name?: string;
  pubDate?: string;
  link?: string;
  sentiment?: string;
}

export interface SentimentFeedResponse {
  symbol: string;
  total_results: number;
  articles: SentimentFeedArticle[];
}

export interface SecFiling {
  symbol?: string;
  cik?: string;
  title?: string;
  acceptedDate?: string;
  filingDate?: string;
  url?: string;
  type?: string;
  finalLink?: string;
}

export interface CompanySearchResult {
  symbol?: string;
  name?: string;
  exchangeShortName?: string;
  stockExchange?: string;
}

interface UpstoxHoldingsResponse {
  data?: UpstoxHolding[];
}

async function getJson<T>(path: string, timeoutMs = 12000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${BACKEND_URL}${path}`, {
      signal: controller.signal,
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new ApiError(`Request failed with status ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("Request timed out");
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError("Could not connect to backend");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function fetchBackendHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function fetchApiStatus(): Promise<ApiStatusResponse> {
  return getJson<ApiStatusResponse>("/api/v1/status");
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
