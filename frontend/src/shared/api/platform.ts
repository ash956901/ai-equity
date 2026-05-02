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
  type PortfolioMetrics,
  type ThematicResult,
  type TimelineEvent,
  type Watchlist,
} from "../types/api";
import { AI_BACKEND_URL, aiDelete, aiGet, aiPost, ApiError } from "./core";

export async function fetchAIHealth(): Promise<HealthResponse> {
  return aiGet<HealthResponse>("/health");
}

export async function fetchThematicScreen(
  query: string,
  limit = 15
): Promise<ThematicResult[]> {
  const params = new URLSearchParams();
  params.set("q", query);
  params.set("limit", String(limit));
  return aiGet<ThematicResult[]>(`/screens/thematic?${params.toString()}`);
}

export async function fetchPortfolioMetrics(
  portfolioId: string
): Promise<PortfolioMetrics> {
  return aiGet<PortfolioMetrics>(`/portfolios/${portfolioId}/metrics`);
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
