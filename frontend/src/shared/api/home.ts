import { getJson } from "./core";

export interface HomeCompany {
  company_id: string;
  name: string;
  ticker_nse?: string | null;
  ticker_bse?: string | null;
  sector?: string | null;
  industry?: string | null;
  market_cap_inr?: number | null;
  quantity?: number | null;
  theme?: string;
  impact_score?: number | null;
  exposure_type?: string | null;
  reasoning?: string;
}

export interface HomeTimelineEvent {
  filing_id: string;
  company_id: string;
  company_name: string;
  ticker_nse?: string | null;
  filing_type: string;
  filing_date?: string | null;
  summary: string;
}

export interface HomePersonalized {
  user: {
    id: string;
    username?: string | null;
    expertise_level: string;
    default_chart_range?: string | null;
  };
  watchlist_companies: HomeCompany[];
  holdings_companies: HomeCompany[];
  asymmetric_feed: HomeCompany[];
  timeline_recent: HomeTimelineEvent[];
  suggestions: HomeCompany[];
  generated_at: string;
}

export async function fetchHomePersonalized(): Promise<HomePersonalized> {
  return getJson<HomePersonalized>("/home/personalized");
}
