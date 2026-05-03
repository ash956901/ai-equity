import { getJson } from "./core";

export interface Candle {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number | null;
}

export interface QuotePayload {
  ticker: string;
  name?: string | null;
  exchange?: string;
  company_id?: string | null;
  sector?: string | null;
  industry?: string | null;
  source?: string;
  last_price?: number | null;
  change_abs?: number | null;
  change_pct?: number | null;
  open?: number | null;
  prev_close?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  volume?: number | null;
  fetched_at?: string;
  message?: string;
  error?: string;
}

export interface CandlesPayload {
  ticker: string;
  exchange: string;
  range: string;
  interval: string;
  source: string;
  ohlcv: Candle[];
  company_id?: string | null;
  fetched_at?: string;
}

export interface PeerCompany {
  company_id: string;
  name: string;
  ticker_nse?: string | null;
  ticker_bse?: string | null;
  sector?: string | null;
  industry?: string | null;
  market_cap_inr?: number | null;
  pe_ratio?: number | null;
  roe?: number | null;
}

export type ChartRange = "1D" | "1W" | "1M" | "6M" | "1Y" | "5Y" | "MAX";

export async function fetchQuote(ticker: string): Promise<QuotePayload> {
  return getJson<QuotePayload>(`/quotes/${encodeURIComponent(ticker)}`);
}

export async function fetchCandles(
  ticker: string,
  range: ChartRange,
  interval?: string,
): Promise<CandlesPayload> {
  const qs = new URLSearchParams({ range });
  if (interval) qs.set("interval", interval);
  return getJson<CandlesPayload>(
    `/quotes/${encodeURIComponent(ticker)}/candles?${qs.toString()}`,
  );
}

export async function fetchPeers(
  ticker: string,
  limit = 8,
): Promise<PeerCompany[]> {
  return getJson<PeerCompany[]>(
    `/quotes/${encodeURIComponent(ticker)}/peers?limit=${limit}`,
  );
}
