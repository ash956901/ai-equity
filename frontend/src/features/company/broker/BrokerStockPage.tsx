import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { fetchCandles, type ChartRange } from "../../../shared/api/quotes";
import { AskMinervaFAB } from "./AskMinervaFAB";
import { BrokerActions } from "./BrokerActions";
import { PeersTab } from "./PeersTab";
import { QuoteHeader } from "./QuoteHeader";
import { RangeToggle } from "./RangeToggle";
import { StockChart, type ChartMode } from "./StockChart";

interface BrokerStockPageProps {
  ticker: string;
  defaultRange?: ChartRange;
  onAskMinerva?: (prompt: string) => void;
  onPickPeer?: (ticker: string) => void;
}

type TabKey = "chart" | "peers";

// Cache TTL by chart range — matches what the backend cache uses, so
// re-clicking 1Y after a quick detour returns instantly.
const STALE_TIME_BY_RANGE: Record<ChartRange, number> = {
  "1D": 60_000, // 1 min
  "1W": 5 * 60_000, // 5 min
  "1M": 60 * 60_000, // 1h
  "6M": 60 * 60_000, // 1h
  "1Y": 24 * 60 * 60_000, // 24h
  "5Y": 24 * 60 * 60_000,
  MAX: 24 * 60 * 60_000,
};

export function BrokerStockPage({
  ticker,
  defaultRange = "1Y",
  onAskMinerva,
  onPickPeer,
}: BrokerStockPageProps) {
  const [range, setRange] = useState<ChartRange>(defaultRange);
  const [mode, setMode] = useState<ChartMode>("line");
  const [companyName, setCompanyName] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("chart");

  const { data: candles, isLoading } = useQuery({
    queryKey: ["candles", ticker, range],
    queryFn: () => fetchCandles(ticker, range),
    staleTime: STALE_TIME_BY_RANGE[range],
    retry: 1,
  });

  return (
    <section className="broker-stock-page">
      <QuoteHeader
        ticker={ticker}
        onCompanyResolved={(_, name) => setCompanyName(name)}
      />

      <div className="broker-stock-page__chart-bar">
        <RangeToggle value={range} onChange={setRange} />
        <div className="broker-stock-page__chart-mode">
          <button
            type="button"
            className={`mode-pill${mode === "line" ? " is-active" : ""}`}
            onClick={() => setMode("line")}
          >
            Line
          </button>
          <button
            type="button"
            className={`mode-pill${mode === "candle" ? " is-active" : ""}`}
            onClick={() => setMode("candle")}
          >
            Candle
          </button>
        </div>
      </div>

      <StockChart data={candles ?? null} loading={isLoading} mode={mode} />

      <BrokerActions ticker={ticker} exchange={candles?.exchange || "NSE"} />

      <nav className="broker-stock-page__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "chart"}
          className={`tab-pill${activeTab === "chart" ? " is-active" : ""}`}
          onClick={() => setActiveTab("chart")}
        >
          Chart
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "peers"}
          className={`tab-pill${activeTab === "peers" ? " is-active" : ""}`}
          onClick={() => setActiveTab("peers")}
        >
          Peers
        </button>
      </nav>

      {activeTab === "peers" ? (
        <PeersTab
          ticker={ticker}
          onSelect={(p) => onPickPeer?.(p.ticker_nse || p.ticker_bse || ticker)}
        />
      ) : null}

      {onAskMinerva ? (
        <AskMinervaFAB ticker={ticker} companyName={companyName} onAsk={onAskMinerva} />
      ) : null}
    </section>
  );
}
