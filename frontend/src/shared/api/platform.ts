import {
  type AICompany,
  type AICompanyListResponse,
  type AIFinancials,
  type AIHolding,
  type AIPortfolio,
  type AIPortfolioDetail,
  type AIRatios,
  type AIQuote,
  type AlertRule,
  type ChatQueryRequest,
  type ChatQueryResponse,
  type ChatSessionItem,
  type CompareRequest,
  type CompareResponse,
  type CreateAlertRequest,
  type HealthResponse,
  type TimelineEvent,
  type Watchlist,
} from "../types/api";
import { aiDelete, aiGet, aiPost, aiUpload } from "./core";

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

export interface InsightCard {
  insight_id: string;
  insight_type: string;
  headline: string;
  narrative?: string | null;
  predicted_direction?: string | null;
  horizon_days?: number | null;
  primary_companies?: { company_id?: string | null; role?: string | null }[];
  related_themes?: string[];
  related_sectors?: string[];
  confidence?: number | null;
  generated_at?: string | null;
  valid_until?: string | null;
  status?: string;
}

export interface InsightFeedResponse {
  total: number;
  limit: number;
  offset: number;
  items: InsightCard[];
}

export interface InsightDetail extends InsightCard {
  evidence_links?: { source_type?: string; source_id?: string; snippet?: string }[];
  counter_evidence?: { source_type?: string; source_id?: string; snippet?: string }[];
  evidence_records?: { source_type: string; source_id?: string | null; snippet?: string | null; weight?: number | null }[];
  confidence_components?: Record<string, number | string | null>;
  related_policies?: unknown[];
}

export async function fetchInsights(params: {
  insightType?: string;
  sector?: string;
  theme?: string;
  limit?: number;
  offset?: number;
  days?: number;
} = {}): Promise<InsightFeedResponse> {
  const search = new URLSearchParams();
  if (params.insightType) search.set("insight_type", params.insightType);
  if (params.sector) search.set("sector", params.sector);
  if (params.theme) search.set("theme", params.theme);
  search.set("limit", String(params.limit ?? 20));
  search.set("offset", String(params.offset ?? 0));
  search.set("days", String(params.days ?? 7));
  return aiGet<InsightFeedResponse>(`/discovery/insights?${search.toString()}`);
}

export async function fetchInsightDetail(insightId: string): Promise<InsightDetail> {
  return aiGet<InsightDetail>(`/discovery/insights/${insightId}`);
}

export async function fetchInsightMetrics(lookbackDays = 30): Promise<{
  lookback_days: number;
  precision_by_type: { insight_type: string; evaluated: number; confirmed: number; contradicted: number; stale: number; precision: number }[];
}> {
  return aiGet(`/discovery/insights/metrics?lookback_days=${lookbackDays}`);
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

  return aiUpload<{ upload_id: string; filename: string; status: string }>(
    "/chat/upload",
    formData,
  );
}
