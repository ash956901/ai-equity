import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  PieChart,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  fetchApiStatus,
  fetchBackendHealth,
  fetchMarketHeadlines,
  fetchPortfolios,
  fetchPortfolioMetrics,
  fetchPortfolioSuggestions,
  fetchTimeline,
  type ApiStatusResponse,
  type HealthResponse,
  type NewsDataResponse,
  type PortfolioMetrics,
  type TimelineEvent,
} from "../../lib/api";

import { PageHeader } from "../../shared/ui/PageHeader";

function getUserId(): string {
  const id = "00000000-0000-0000-0000-000000000001";
  localStorage.setItem("equityai-user-id", id);
  return id;
}

interface DashboardWidget {
  id: string;
  label: string;
}

interface DashboardPreferences {
  density: "comfortable" | "compact";
  hiddenWidgets: string[];
}

const DASHBOARD_WIDGETS: DashboardWidget[] = [
  { id: "kpi-row", label: "KPI Summary" },
  { id: "holdings-pnl", label: "Holdings P&L" },
  { id: "sector-allocation", label: "Sector Allocation" },
  { id: "risk-metrics", label: "Risk Metrics" },
  { id: "ai-insight", label: "AI Insights" },
  { id: "ai-suggestions", label: "Investment Suggestions" },
  { id: "market-headlines", label: "Market Headlines" },
];

const DEMO_BANNER_MSG =
  "Demo mode — showing cached data. Switch to Live API for real-time results.";

interface DashboardViewProps {
  dataMode: "live" | "demo";
  preferences: DashboardPreferences;
  onToggleDensity: () => void;
  onToggleWidget: (widgetId: string) => void;
  onResetPreferences: () => void;
}

// Types for enriched holdings returned by portfolio metrics
interface HoldingDetail {
  ticker_nse: string;
  company_name: string;
  sector: string;
  weight: number;
  return_pct: number;
  quantity: number;
  average_price: number;
  current_price: number;
  value: number;
}

export function DashboardView(props: DashboardViewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse>({});
  const [apiStatus, setApiStatus] = useState<ApiStatusResponse>({});
  const [headlines, setHeadlines] = useState<NewsDataResponse>({});
  const [portfolioMetrics, setPortfolioMetrics] =
    useState<PortfolioMetrics | null>(null);
  const [aiSuggestions, setAiSuggestions] = useState<string | null>(null);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);


  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (props.dataMode === "demo") {
      setHealth({ status: "demo", message: DEMO_BANNER_MSG });
      setApiStatus({ api_version: "demo", status: "demo" });
      setHeadlines({});
      setLoading(false);
      return;
    }

    const [healthRes, apiRes, headlinesRes, timelineRes] = await Promise.allSettled([
      fetchBackendHealth(),
      fetchApiStatus(),
      fetchMarketHeadlines(),
      fetchTimeline(getUserId(), undefined, 10),
    ]);

    if (healthRes.status === "fulfilled") setHealth(healthRes.value);
    if (apiRes.status === "fulfilled") setApiStatus(apiRes.value);
    if (headlinesRes.status === "fulfilled") setHeadlines(headlinesRes.value);
    if (timelineRes.status === "fulfilled") setTimelineEvents(timelineRes.value);


    try {
      const list = await fetchPortfolios(getUserId());
      if (list.length > 0) {
        const primary = list.find((p) => p.is_primary) ?? list[0];
        const metrics = await fetchPortfolioMetrics(primary.id);
        setPortfolioMetrics(metrics);
        
        // Fetch AI suggestions separately as it might take longer
        setSuggestionsLoading(true);
        fetchPortfolioSuggestions(getUserId())
          .then(res => setAiSuggestions(res.suggestions))
          .catch(err => console.error("Failed to load suggestions", err))
          .finally(() => setSuggestionsLoading(false));
      }
    } catch (e) {
      console.error("Failed to load portfolio metrics", e);
    }

    const failedCount = [healthRes, apiRes, headlinesRes].filter(
      (result) => result.status === "rejected"
    ).length;

    if (failedCount === 3) {
      setError(
        "Could not connect to backend services. Check server status."
      );
    } else if (failedCount > 0) {
      setError("Some widgets are unavailable right now.");
    }

    setLoading(false);
  }, [props.dataMode]);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  const isWidgetVisible = useCallback(
    (id: string) => !props.preferences.hiddenWidgets.includes(id),
    [props.preferences.hiddenWidgets]
  );

  const cardDensityClass =
    props.preferences.density === "compact" ? "card-compact" : "";

  // Derived data
  const holdings: HoldingDetail[] = (
    (portfolioMetrics as any)?.holdings ?? []
  ).map((h: any) => ({
    ticker_nse: h.ticker_nse ?? "—",
    company_name: h.company_name ?? "Unknown",
    sector: h.sector ?? "Unknown",
    weight: h.weight ?? 0,
    return_pct: h.return_pct ?? 0,
    quantity: h.quantity ?? 0,
    average_price: h.average_price ?? 0,
    current_price: h.current_price ?? 0,
    value: h.value ?? 0,
  }));

  const totalInvested = holdings.reduce(
    (sum: number, h: HoldingDetail) => sum + h.quantity * h.average_price,
    0
  );
  const totalCurrent = portfolioMetrics?.total_value_inr ?? 0;
  const totalPnl = totalCurrent - totalInvested;
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;

  const topGainers = [...holdings]
    .sort((a, b) => b.return_pct - a.return_pct)
    .slice(0, 3);
  const topLosers = [...holdings]
    .sort((a, b) => a.return_pct - b.return_pct)
    .slice(0, 3);

  // Sector allocation from metrics
  const sectorAllocation: Record<string, number> =
    (portfolioMetrics as any)?.sector_allocation ?? {};

  const headlineCount =
    headlines.results?.length ?? headlines.totalResults ?? 0;
  const latestHeadlines = headlines.results?.slice(0, 5) ?? [];

  const formatINR = (value: number) => {
    if (Math.abs(value) >= 1e7)
      return `₹${(value / 1e7).toFixed(2)} Cr`;
    if (Math.abs(value) >= 1e5)
      return `₹${(value / 1e5).toFixed(2)} L`;
    return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Market Command Center"
        subtitle="Portfolio intelligence, risk analytics, and market signals — all in one view."
        dataMode={props.dataMode}
        right={
          <div className="dashboard-actions">
            <button
              type="button"
              className="secondary-btn mini-btn"
              onClick={props.onToggleDensity}
            >
              Density: {props.preferences.density}
            </button>
            <button
              type="button"
              className="secondary-btn mini-btn"
              onClick={props.onResetPreferences}
            >
              Reset Layout
            </button>
            <button
              type="button"
              className="primary-btn"
              onClick={() => void loadDashboardData()}
            >
              {loading ? "Refreshing..." : "Refresh Data"}
            </button>
          </div>
        }
      />

      <div className="dashboard-widget-toggles">
        {DASHBOARD_WIDGETS.map((widget) => (
          <button
            key={widget.id}
            type="button"
            className={`widget-toggle-chip ${isWidgetVisible(widget.id) ? "active" : ""}`}
            onClick={() => props.onToggleWidget(widget.id)}
          >
            {widget.label}
          </button>
        ))}
      </div>

      {error ? <div className="notice warning">{error}</div> : null}

      {/* ── KPI Summary Row ── */}
      {isWidgetVisible("kpi-row") ? (
        <div className="kpi-grid">
          <article className={`kpi-card ${cardDensityClass}`}>
            <p><Wallet size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />Current Value</p>
            <h2>{loading ? "--" : formatINR(totalCurrent)}</h2>
            <small>
              {portfolioMetrics
                ? `${portfolioMetrics.holdings_count} stocks`
                : "No holdings"}
            </small>
          </article>

          <article className={`kpi-card ${cardDensityClass}`}>
            <p><Activity size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />Invested</p>
            <h2>{loading ? "--" : formatINR(totalInvested)}</h2>
            <small>Total cost basis</small>
          </article>

          <article className={`kpi-card ${cardDensityClass}`}>
            <p>
              {totalPnl >= 0 ? (
                <TrendingUp size={14} style={{ verticalAlign: "middle", marginRight: 4, color: "var(--good)" }} />
              ) : (
                <TrendingDown size={14} style={{ verticalAlign: "middle", marginRight: 4, color: "var(--bad)" }} />
              )}
              Overall P&L
            </p>
            <h2
              style={{
                color: totalPnl >= 0 ? "var(--good)" : "var(--bad)",
              }}
            >
              {loading
                ? "--"
                : `${totalPnl >= 0 ? "+" : ""}${formatINR(totalPnl)}`}
            </h2>
            <small
              style={{
                color: totalPnl >= 0 ? "var(--good)" : "var(--bad)",
              }}
            >
              {totalPnlPct >= 0 ? "+" : ""}
              {totalPnlPct.toFixed(2)}%
            </small>
          </article>

          <article className={`kpi-card ${cardDensityClass}`}>
            <p><TrendingUp size={14} style={{ verticalAlign: "middle", marginRight: 4 }} />Headlines</p>
            <h2>{loading ? "--" : headlineCount}</h2>
            <small>Live market news</small>
          </article>
        </div>
      ) : null}

      {/* ── Holdings P&L Table ── */}
      {isWidgetVisible("holdings-pnl") && !loading && holdings.length > 0 ? (
        <article className={`feature-card ${cardDensityClass}`} style={{ marginTop: 16 }}>
          <div className="feature-head">
            <BarChart3 size={18} />
            <h3>Holdings P&L Breakdown</h3>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table className="holdings-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)", opacity: 0.7 }}>
                  <th style={{ padding: "8px 10px" }}>Stock</th>
                  <th style={{ padding: "8px 10px" }}>Qty</th>
                  <th style={{ padding: "8px 10px" }}>Avg Cost</th>
                  <th style={{ padding: "8px 10px" }}>CMP</th>
                  <th style={{ padding: "8px 10px" }}>Invested</th>
                  <th style={{ padding: "8px 10px" }}>Current</th>
                  <th style={{ padding: "8px 10px" }}>P&L</th>
                  <th style={{ padding: "8px 10px" }}>P&L %</th>
                  <th style={{ padding: "8px 10px" }}>Weight</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => {
                  const invested = h.quantity * h.average_price;
                  const pnl = h.value - invested;
                  const pnlColor = pnl >= 0 ? "var(--good)" : "var(--bad)";
                  return (
                    <tr
                      key={h.ticker_nse}
                      style={{ borderBottom: "1px solid var(--border)" }}
                    >
                      <td style={{ padding: "8px 10px", fontWeight: 600 }}>
                        {h.ticker_nse}
                        <br />
                        <span style={{ fontWeight: 400, fontSize: 11, opacity: 0.6 }}>
                          {h.company_name}
                        </span>
                      </td>
                      <td style={{ padding: "8px 10px" }}>{h.quantity}</td>
                      <td style={{ padding: "8px 10px" }}>
                        ₹{h.average_price.toLocaleString("en-IN")}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        ₹{h.current_price.toLocaleString("en-IN")}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        {formatINR(invested)}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        {formatINR(h.value)}
                      </td>
                      <td style={{ padding: "8px 10px", color: pnlColor, fontWeight: 600 }}>
                        {pnl >= 0 ? "+" : ""}
                        {formatINR(pnl)}
                      </td>
                      <td style={{ padding: "8px 10px", color: pnlColor }}>
                        {h.return_pct >= 0 ? "+" : ""}
                        {h.return_pct.toFixed(2)}%
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        {h.weight.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr style={{ fontWeight: 700, borderTop: "2px solid var(--border)" }}>
                  <td style={{ padding: "8px 10px" }}>Total</td>
                  <td style={{ padding: "8px 10px" }}>{holdings.reduce((s, h) => s + h.quantity, 0)}</td>
                  <td style={{ padding: "8px 10px" }}></td>
                  <td style={{ padding: "8px 10px" }}></td>
                  <td style={{ padding: "8px 10px" }}>{formatINR(totalInvested)}</td>
                  <td style={{ padding: "8px 10px" }}>{formatINR(totalCurrent)}</td>
                  <td
                    style={{
                      padding: "8px 10px",
                      color: totalPnl >= 0 ? "var(--good)" : "var(--bad)",
                    }}
                  >
                    {totalPnl >= 0 ? "+" : ""}
                    {formatINR(totalPnl)}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      color: totalPnl >= 0 ? "var(--good)" : "var(--bad)",
                    }}
                  >
                    {totalPnlPct >= 0 ? "+" : ""}
                    {totalPnlPct.toFixed(2)}%
                  </td>
                  <td style={{ padding: "8px 10px" }}>100%</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </article>
      ) : null}

      <div className="split-grid" style={{ marginTop: 16 }}>
        {/* ── Sector Allocation ── */}
        {isWidgetVisible("sector-allocation") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <PieChart size={18} />
              <h3>Sector Allocation</h3>
            </div>
            {Object.keys(sectorAllocation).length > 0 ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {Object.entries(sectorAllocation)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .map(([sector, weight]) => {
                    const pct = ((weight as number) * 100).toFixed(1);
                    return (
                      <div key={sector}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: 13,
                            marginBottom: 3,
                          }}
                        >
                          <span>{sector}</span>
                          <strong>{pct}%</strong>
                        </div>
                        <div
                          style={{
                            height: 6,
                            borderRadius: 3,
                            background: "var(--bg-layer-1)",
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              width: `${pct}%`,
                              height: "100%",
                              borderRadius: 3,
                              background:
                                "linear-gradient(90deg, var(--brand), var(--accent-light, var(--brand)))",
                              transition: "width 0.5s ease",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <p>No sector data available.</p>
            )}
          </article>
        ) : null}

        {/* ── Risk Metrics ── */}
        {isWidgetVisible("risk-metrics") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <ShieldCheck size={18} />
              <h3>Risk Metrics</h3>
            </div>
            {portfolioMetrics ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div className="risk-metric-row">
                  <span>Portfolio Beta</span>
                  <strong>{portfolioMetrics.portfolio_beta.toFixed(2)}</strong>
                </div>
                <div className="risk-metric-row">
                  <span>Volatility</span>
                  <strong>
                    {((portfolioMetrics.portfolio_volatility ?? 0) * 100).toFixed(1)}%
                  </strong>
                </div>
                <div className="risk-metric-row">
                  <span>Sharpe Ratio</span>
                  <strong>{(portfolioMetrics.sharpe_ratio ?? 0).toFixed(2)}</strong>
                </div>
                <div className="risk-metric-row">
                  <span>Diversification</span>
                  <strong>{portfolioMetrics.diversification_score}/100</strong>
                </div>
                <div className="risk-metric-row">
                  <span>Top Holding Concentration</span>
                  <strong>
                    {(portfolioMetrics.top_holding_pct * 100).toFixed(1)}%
                  </strong>
                </div>
                <div className="risk-metric-row">
                  <span>Backend Status</span>
                  <strong style={{ color: health.status === "healthy" ? "var(--good)" : "inherit" }}>
                    {health.status ?? "unknown"} · v{apiStatus.api_version ?? "n/a"}
                  </strong>
                </div>
              </div>
            ) : (
              <p>Load a portfolio to see risk analysis.</p>
            )}
          </article>
        ) : null}
      </div>

      <div className="split-grid" style={{ marginTop: 16 }}>
        {/* ── AI Insights ── */}
        {isWidgetVisible("ai-insight") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>AI Portfolio Insights</h3>
            </div>
            {portfolioMetrics ? (
              <div className="ai-insight-content">
                <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
                  <div className="insight-mini-card">
                    <span className="insight-mini-label">Top Gainer</span>
                    {topGainers[0] && (
                      <>
                        <strong style={{ color: "var(--green)" }}>
                          {topGainers[0].ticker_nse}
                        </strong>
                        <span style={{ color: "var(--green)", fontSize: 12 }}>
                          +{topGainers[0].return_pct.toFixed(1)}%
                        </span>
                      </>
                    )}
                  </div>
                  <div className="insight-mini-card">
                    <span className="insight-mini-label">Top Loser</span>
                    {topLosers[0] && (
                      <>
                        <strong
                          style={{
                            color:
                              topLosers[0].return_pct < 0
                                ? "var(--red)"
                                : "var(--green)",
                          }}
                        >
                          {topLosers[0].ticker_nse}
                        </strong>
                        <span
                          style={{
                            color:
                              topLosers[0].return_pct < 0
                                ? "var(--red)"
                                : "var(--green)",
                            fontSize: 12,
                          }}
                        >
                          {topLosers[0].return_pct >= 0 ? "+" : ""}
                          {topLosers[0].return_pct.toFixed(1)}%
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <p style={{ fontSize: 13, lineHeight: 1.6 }}>
                  Your portfolio has a beta of{" "}
                  <strong>
                    {portfolioMetrics.portfolio_beta.toFixed(2)}
                  </strong>
                  , implying it tracks the market closely. Top holding accounts
                  for{" "}
                  <strong>
                    {(portfolioMetrics.top_holding_pct * 100).toFixed(1)}%
                  </strong>{" "}
                  of capital.{" "}
                  {portfolioMetrics.diversification_score >= 70
                    ? "Diversification score is healthy."
                    : "Consider adding more sectors to reduce concentration risk."}
                </p>
                {portfolioMetrics.top_holding_pct > 0.4 ? (
                  <p
                    className="notice warning"
                    style={{ marginTop: 8, padding: 6 }}
                  >
                    ⚠️ High concentration detected. Consider rebalancing to
                    reduce single-stock risk.
                  </p>
                ) : (
                  <p
                    className="notice"
                    style={{ marginTop: 8, padding: 6 }}
                  >
                    ✅ Portfolio is well-diversified (
                    {portfolioMetrics.diversification_score}/100).
                  </p>
                )}
              </div>
            ) : (
              <p>
                Connect a portfolio to receive AI-driven insights on
                concentration and risk.
              </p>
            )}
          </article>
        ) : null}

        {/* ── AI Investment Suggestions ── */}
        {isWidgetVisible("ai-suggestions") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <ShieldCheck size={18} />
              <h3>AI Investment Suggestions</h3>
            </div>
            <div className="ai-insight-content">
              {suggestionsLoading ? (
                <div className="loading-shimmer" style={{ height: 120, borderRadius: 8 }}>
                  <p style={{ padding: 20 }}>Iris is analyzing news and portfolio...</p>
                </div>
              ) : aiSuggestions ? (
                <div className="markdown-body" style={{ fontSize: 13, lineHeight: 1.6 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {aiSuggestions}
                  </ReactMarkdown>
                </div>
              ) : (
                <p>No suggestions available at this time.</p>
              )}
            </div>
          </article>
        ) : null}

        {/* ── Market Signals & Alerts ── */}
        {isWidgetVisible("market-headlines") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Market Signals & Alerts</h3>
            </div>
            {loading ? (
              <p>Loading market signals...</p>
            ) : timelineEvents.length > 0 ? (
              <ul
                className="market-signal-list"
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                {timelineEvents.slice(0, 8).map((event: any) => (
                  <li
                    key={event.id}
                    className={`signal-item signal-${event.event_type}`}
                    style={{
                      padding: "10px 12px",
                      background: "var(--bg-elevated)",
                      borderRadius: 10,
                      fontSize: 13,
                      lineHeight: 1.5,
                      borderLeft: `4px solid ${
                        event.event_type === "signal" ? "#ef8f36" : 
                        event.event_type === "filing" ? "var(--brand)" : "#7f5af0"
                      }`,
                      display: "flex",
                      flexDirection: "column",
                      gap: 4
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: 11, textTransform: "uppercase", color: "var(--muted)" }}>
                        {event.company_name ?? "General Market"} · {event.event_type}
                      </strong>
                      <span style={{ fontSize: 10, color: "var(--muted)" }}>
                        {new Date(event.timestamp).toLocaleDateString()}
                      </span>
                    </div>
                    <span style={{ fontWeight: 600 }}>{event.title}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No signals available.</p>
            )}
          </article>
        ) : null}

      </div>
    </section>
  );
}
