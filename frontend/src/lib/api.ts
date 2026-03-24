export const BACKEND_URL =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
  "http://localhost:8001";

/** @deprecated Use BACKEND_URL — all APIs now run on a single server. */
export const AI_BACKEND_URL = BACKEND_URL;

export class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface DataSourceInfo {
  name: string;
  url: string;
  data_type: string;
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

/* ── AI Backend types ── */

export interface ChatQueryRequest {
  user_id: string;
  session_id?: string;
  query: string;
  expertise_level?: "beginner" | "intermediate" | "advanced";
  upload_id?: string;
}

export interface ChatQueryResponse {
  response: string;
  sources: Record<string, unknown>[];
  visualizations: string[];
  tokens_used: number;
  session_id: string;
  execution_plan: string[];
  agent_call_log: Record<string, unknown>[];
  tool_call_log: Record<string, unknown>[];
  agent_outputs: Record<string, unknown>;
  data_sources?: DataSourceInfo[];
}

export interface ChatSessionItem {
  id: string;
  title: string;
  context_type: string;
  last_message_at: string | null;
  created_at: string;
}

export interface AICompany {
  id: string;
  name: string;
  ticker_nse?: string;
  ticker_bse?: string;
  isin?: string;
  sector?: string;
  industry?: string;
  sub_industry?: string;
  market_cap_inr?: number;
  legal_name?: string;
  website_domain?: string;
  ir_page_url?: string;
  description?: string;
  listing_status?: string;
  data_sources?: DataSourceInfo[];
}

export interface AICompanyListResponse {
  total: number;
  offset: number;
  limit: number;
  companies: AICompany[];
}

export interface AIQuote {
  company_id: string;
  name?: string;
  source?: string;
  last_price?: number;
  change?: number;
  change_pct?: number;
  volume?: number;
  market_cap?: number;
  fetched_at?: string;
  data_sources?: DataSourceInfo[];
}

export interface AIFinancials {
  company_id: string;
  company_name: string;
  latest_period: string | null;
  source?: string;
  periods: {
    period_end: string;
    items: { line_item: string; value: number | null; unit: string; statement_type: string }[];
  }[];
  data_sources?: DataSourceInfo[];
}

export interface AIRatios {
  company_id: string;
  company_name: string;
  period_end?: string;
  fiscal_year?: number;
  source?: string;
  ratios: Record<string, number | null>;
  data_sources?: DataSourceInfo[];
}

export interface AIPortfolio {
  id: string;
  name: string;
  description?: string;
  broker?: string;
  is_primary: boolean;
}

export interface AIPortfolioDetail extends AIPortfolio {
  holdings: AIHoldingDetail[];
  metrics: Record<string, unknown>;
  data_sources?: DataSourceInfo[];
}

export interface AIHolding {
  id: string;
  company_id: string;
  quantity: number;
  average_price?: number;
  current_price?: number;
}

export interface AIHoldingDetail {
  id: string;
  company_id: string;
  company_name?: string;
  ticker_nse?: string;
  sector?: string;
  quantity: number;
  average_price?: number;
  current_price?: number;
  weight?: number;
  return_pct?: number;
}

export interface CompareRequest {
  user_id: string;
  company_ids: string[];
  query?: string;
  expertise_level?: string;
}

export interface CompareResponse {
  response: string;
  tokens_used: number;
}

export interface AlertRule {
  id: string;
  user_id: string;
  name: string;
  condition_type: string;
  condition_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  last_triggered_at?: string;
}

export interface CreateAlertRequest {
  user_id: string;
  name: string;
  condition_type: string;
  condition_config?: Record<string, unknown>;
  is_active?: boolean;
}

export interface Watchlist {
  id: string;
  user_id: string;
  name: string;
  companies: string[];
  created_at: string;
}

export interface TimelineEvent {
  id: string;
  event_type: string;
  title: string;
  summary: string;
  timestamp: string;
  company_id?: string;
  company_name?: string;
  metadata?: Record<string, unknown>;
  data_sources?: DataSourceInfo[];
}

/* ── Generic fetch helpers ── */

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

async function aiGet<T>(path: string, timeoutMs = 30000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${AI_BACKEND_URL}${path}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new ApiError(`AI request failed with status ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("AI request timed out");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not connect to AI backend");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function aiPost<T>(path: string, body: unknown, timeoutMs = 60000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${AI_BACKEND_URL}${path}`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new ApiError(`AI request failed with status ${response.status}`, response.status);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("AI request timed out");
    }
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not connect to AI backend");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function aiDelete(path: string): Promise<void> {
  const response = await fetch(`${AI_BACKEND_URL}${path}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new ApiError(`Delete failed with status ${response.status}`, response.status);
  }
}

/* ── External data APIs (FMP, FRED, NewsAPI, NewsDataIO, Upstox, Kite) ── */

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

/* ── AI & platform APIs ── */

export async function fetchAIHealth(): Promise<HealthResponse> {
  return aiGet<HealthResponse>("/health");
}

export async function sendChatQuery(req: ChatQueryRequest): Promise<ChatQueryResponse> {
  return aiPost<ChatQueryResponse>("/chat/query", req);
}

export async function listChatSessions(userId: string): Promise<ChatSessionItem[]> {
  return aiGet<ChatSessionItem[]>(`/chat/sessions/${userId}`);
}

export async function fetchCompanies(
  limit = 50,
  offset = 0,
  search?: string,
  sector?: string
): Promise<AICompanyListResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (search) params.set("search", search);
  if (sector) params.set("sector", sector);
  return aiGet<AICompanyListResponse>(`/companies/?${params.toString()}`);
}

export async function fetchCompanyDetail(id: string): Promise<AICompany> {
  return aiGet<AICompany>(`/companies/${id}`);
}

export async function fetchCompanyFinancials(id: string, periods = 4): Promise<AIFinancials> {
  return aiGet<AIFinancials>(`/companies/${id}/financials?periods=${periods}`);
}

export async function fetchCompanyRatios(id: string): Promise<AIRatios> {
  return aiGet<AIRatios>(`/companies/${id}/ratios`);
}

export async function fetchCompanyQuote(id: string): Promise<AIQuote> {
  return aiGet<AIQuote>(`/companies/${id}/quote`);
}

export async function enrichCompany(
  id: string
): Promise<{ company_id: string; enriched: boolean; updated_fields?: string[]; source?: string }> {
  return aiPost(`/companies/${id}/enrich`, {});
}

export async function searchCompaniesDB(
  query: string,
  limit = 20
): Promise<AICompany[]> {
  const params = new URLSearchParams();
  params.set("q", query);
  params.set("limit", String(limit));
  return aiGet<AICompany[]>(`/companies/search?${params.toString()}`);
}

export async function fetchPortfolios(userId: string): Promise<AIPortfolio[]> {
  return aiGet<AIPortfolio[]>(`/portfolios/?user_id=${userId}`);
}

export async function createPortfolio(userId: string, name: string): Promise<AIPortfolio> {
  return aiPost<AIPortfolio>("/portfolios/", { user_id: userId, name });
}

export async function fetchPortfolioDetail(id: string): Promise<AIPortfolioDetail> {
  return aiGet<AIPortfolioDetail>(`/portfolios/${id}`);
}

export async function addHolding(
  portfolioId: string,
  companyId: string,
  quantity: number,
  averagePrice?: number
): Promise<AIHolding> {
  return aiPost<AIHolding>(`/portfolios/${portfolioId}/holdings`, {
    company_id: companyId,
    quantity,
    average_price: averagePrice,
  });
}

export async function compareCompanies(req: CompareRequest): Promise<CompareResponse> {
  return aiPost<CompareResponse>("/compare/", req);
}

export async function createAlertRule(req: CreateAlertRequest): Promise<AlertRule> {
  return aiPost<AlertRule>("/alerts/", req);
}

export async function fetchAlerts(userId: string): Promise<AlertRule[]> {
  return aiGet<AlertRule[]>(`/alerts/?user_id=${userId}`);
}

export async function createAlert(alert: Omit<AlertRule, "id" | "created_at">): Promise<AlertRule> {
  return aiPost<AlertRule>("/alerts/", alert);
}

export async function deleteAlert(id: string): Promise<void> {
  return aiDelete(`/alerts/${id}`);
}

export async function fetchWatchlists(userId: string): Promise<Watchlist[]> {
  return aiGet<Watchlist[]>(`/watchlists/?user_id=${userId}`);
}

export async function createWatchlist(userId: string, name: string): Promise<Watchlist> {
  return aiPost<Watchlist>("/watchlists/", { user_id: userId, name });
}

export async function addToWatchlist(watchlistId: string, companyId: string): Promise<void> {
  await aiPost(`/watchlists/${watchlistId}/companies`, { company_id: companyId });
}

export async function removeFromWatchlist(watchlistId: string, companyId: string): Promise<void> {
  return aiDelete(`/watchlists/${watchlistId}/companies/${companyId}`);
}

export async function fetchTimeline(
  userId?: string,
  companyId?: string,
  limit = 20
): Promise<TimelineEvent[]> {
  const params = new URLSearchParams();
  if (userId) params.set("user_id", userId);
  if (companyId) params.set("company_id", companyId);
  params.set("limit", String(limit));
  return aiGet<TimelineEvent[]>(`/timeline/?${params.toString()}`);
}

export async function uploadDocument(
  userId: string,
  file: File,
  sessionId?: string
): Promise<{ upload_id: string; filename: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", userId);
  if (sessionId) formData.append("session_id", sessionId);

  const response = await fetch(`${AI_BACKEND_URL}/chat/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(`Upload failed with status ${response.status}`, response.status);
  }

  return response.json();
}

/* ── User Profile APIs ── */

export interface UserProfile {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  phone_number: string | null;
  date_of_birth: string | null;
  address: string | null;
  pan_card_number: string | null;
  aadhaar_number: string | null;
  profile_pic_url: string | null;
  expertise_level: string;
  risk_tolerance: string | null;
  investment_horizon: string | null;
  kyc_status: string;
  kyc_submitted_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserProfileUpdate {
  username?: string;
  full_name?: string;
  email?: string;
  phone_number?: string;
  date_of_birth?: string;
  address?: string;
  pan_card_number?: string;
  aadhaar_number?: string;
  expertise_level?: string;
  risk_tolerance?: string;
  investment_horizon?: string;
}

export async function fetchUserProfile(userId: string): Promise<UserProfile> {
  return aiGet<UserProfile>(`/users/${userId}`);
}

export async function updateUserProfile(
  userId: string,
  data: UserProfileUpdate
): Promise<UserProfile> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(`${AI_BACKEND_URL}/users/${userId}`, {
      method: "PUT",
      signal: controller.signal,
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok)
      throw new ApiError(`Profile update failed with status ${response.status}`, response.status);
    return (await response.json()) as UserProfile;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError("Could not update profile");
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function uploadProfilePic(
  userId: string,
  file: File
): Promise<{ profile_pic_url: string }> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${AI_BACKEND_URL}/users/${userId}/profile-pic`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok)
    throw new ApiError(`Profile pic upload failed with status ${response.status}`, response.status);
  return response.json();
}

export async function submitKyc(
  userId: string,
  panCardNumber: string,
  aadhaarNumber?: string
): Promise<{ kyc_status: string; kyc_submitted_at: string; message: string }> {
  return aiPost(`/users/${userId}/kyc/submit`, {
    pan_card_number: panCardNumber,
    aadhaar_number: aadhaarNumber,
  });
}

export async function fetchKycStatus(
  userId: string
): Promise<{ kyc_status: string; kyc_submitted_at: string | null; pan_card_number: string | null }> {
  return aiGet(`/users/${userId}/kyc/status`);
}

export async function verifyKyc(
  userId: string
): Promise<{ kyc_status: string; message: string }> {
  return aiPost(`/users/${userId}/kyc/verify`, {});
}
