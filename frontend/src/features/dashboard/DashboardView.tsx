import { useCallback, useEffect, useState } from "react";
import { BarChart3, TrendingUp } from "lucide-react";

import {
  fetchApiStatus,
  fetchBackendHealth,
  fetchHoldingsCount,
  fetchMarketHeadlines,
  type ApiStatusResponse,
  type HealthResponse,
  type NewsDataResponse,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";

interface DashboardWidget {
  id: string;
  label: string;
}

interface DashboardPreferences {
  density: "comfortable" | "compact";
  hiddenWidgets: string[];
}

const DASHBOARD_WIDGETS: DashboardWidget[] = [
  { id: "kpi-portfolio", label: "Portfolio Companies" },
  { id: "kpi-headlines", label: "Live Headlines" },
  { id: "kpi-health", label: "Backend Health" },
  { id: "kpi-api", label: "API Version" },
  { id: "feature-concentration", label: "Portfolio Concentration" },
  { id: "feature-headline", label: "Latest Market Headline" },
];

const DEMO_BANNER_MSG = "Demo mode — showing cached data. Switch to Live API for real-time results.";

interface DashboardViewProps {
  dataMode: "live" | "demo";
  preferences: DashboardPreferences;
  onToggleDensity: () => void;
  onToggleWidget: (widgetId: string) => void;
  onResetPreferences: () => void;
}

export function DashboardView(props: DashboardViewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse>({});
  const [apiStatus, setApiStatus] = useState<ApiStatusResponse>({});
  const [headlines, setHeadlines] = useState<NewsDataResponse>({});
  const [holdingsCount, setHoldingsCount] = useState<number>(0);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    if (props.dataMode === "demo") {
      setHealth({ status: "demo", message: DEMO_BANNER_MSG });
      setApiStatus({ api_version: "demo", status: "demo" });
      setHeadlines({});
      setHoldingsCount(0);
      setLoading(false);
      return;
    }

    const [healthRes, apiRes, headlinesRes, holdingsRes] = await Promise.allSettled([
      fetchBackendHealth(),
      fetchApiStatus(),
      fetchMarketHeadlines(),
      fetchHoldingsCount(),
    ]);

    if (healthRes.status === "fulfilled") setHealth(healthRes.value);
    if (apiRes.status === "fulfilled") setApiStatus(apiRes.value);
    if (headlinesRes.status === "fulfilled") setHeadlines(headlinesRes.value);
    if (holdingsRes.status === "fulfilled") setHoldingsCount(holdingsRes.value);

    const failedCount = [healthRes, apiRes, headlinesRes, holdingsRes].filter(
      (result) => result.status === "rejected"
    ).length;

    if (failedCount === 4) {
      setError("Could not connect to backend services. Check server status.");
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

  const cardDensityClass = props.preferences.density === "compact" ? "card-compact" : "";

  const headlineCount = headlines.results?.length ?? headlines.totalResults ?? 0;
  const latestHeadline = headlines.results?.[0]?.title ?? "No headlines yet";

  return (
    <section className="page-wrap">
      <PageHeader
        title="Market Command Center"
        subtitle="Track activity, spot risks, and jump into analysis flows quickly."
        dataMode={props.dataMode}
        right={
          <div className="dashboard-actions">
            <button type="button" className="secondary-btn mini-btn" onClick={props.onToggleDensity}>
              Density: {props.preferences.density}
            </button>
            <button type="button" className="secondary-btn mini-btn" onClick={props.onResetPreferences}>
              Reset Layout
            </button>
            <button type="button" className="primary-btn" onClick={() => void loadDashboardData()}>
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

      <div className="kpi-grid">
        {isWidgetVisible("kpi-portfolio") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Portfolio Companies</p>
            <h2>{loading ? "--" : holdingsCount}</h2>
            <small>From Upstox holdings</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-headlines") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Live Headlines</p>
            <h2>{loading ? "--" : headlineCount}</h2>
            <small>From NewsData market feed</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-health") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Backend Health</p>
            <h2>{loading ? "--" : (health.status ?? "unknown")}</h2>
            <small>{health.message ?? "No status message"}</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-api") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>API Version</p>
            <h2>{loading ? "--" : (apiStatus.api_version ?? "n/a")}</h2>
            <small>Status: {apiStatus.status ?? "unknown"}</small>
          </article>
        ) : null}
      </div>

      <div className="split-grid">
        {isWidgetVisible("feature-concentration") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>Portfolio Concentration</h3>
            </div>
            <p>
              Top 3 positions account for 47% of capital. Consider rebalancing to reduce concentration risk.
            </p>
          </article>
        ) : null}

        {isWidgetVisible("feature-headline") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Latest Market Headline</h3>
            </div>
            <p>{loading ? "Loading latest headline..." : latestHeadline}</p>
          </article>
        ) : null}
      </div>
    </section>
  );
}
