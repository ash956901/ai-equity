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

export interface EnrichedNewsItem {
  title: string;
  summary: string;
  url?: string | null;
  source: string;
  source_feed: string;
  published_at: string;
  sentiment: string;
  sentiment_confidence: number;
  categories: string[];
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
  gemini_extra?: Record<string, string[]>;
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

export interface AIHistoricalPrice {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface AIHistoricalPrices {
  company_id: string;
  company_name: string;
  symbol?: string;
  source?: string;
  days_requested: number;
  prices: AIHistoricalPrice[];
  data_sources?: DataSourceInfo[];
  error?: string;
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
  company_names: string[];
  query?: string;
  expertise_level?: string;
}

export type CompareWinner = "A" | "B" | "Tie";

export interface CompareResponse {
  companyA_summary: string;
  companyB_summary: string;
  comparison: {
    growth: CompareWinner;
    profitability: CompareWinner;
    risk: CompareWinner;
    valuation: CompareWinner;
  };
  insights: string[];
  final_verdict: string;
  companyA_stock_data: Record<string, unknown>;
  companyB_stock_data: Record<string, unknown>;
  detailed_comparison: Record<string, string>;
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

export interface ThematicResult {
  company_id: string;
  company_name: string;
  ticker_nse?: string;
  ticker_bse?: string;
  sector?: string;
  industry?: string;
  market_cap_inr?: number;
  relevance_score: number;
  match_count: number;
  evidence_snippets: string[];
}

export interface PortfolioMetrics {
  portfolio_id: string;
  portfolio_name: string;
  total_value_inr: number;
  holdings_count: number;
  top_holding_pct: number;
  portfolio_beta: number;
  portfolio_volatility: number;
  sharpe_ratio: number;
  diversification_score: number;
  sector_allocation: Record<string, number>;
  holdings: AIHoldingDetail[];
}

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

export interface ProfileOption {
  value: string;
  label: string;
}

export interface ProfileConfigResponse {
  expertise_levels: ProfileOption[];
  risk_tolerance_levels: ProfileOption[];
  investment_horizons: ProfileOption[];
  kyc_statuses: ProfileOption[];
  defaults: Record<string, string>;
}
