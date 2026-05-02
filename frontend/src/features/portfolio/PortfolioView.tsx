import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, Compass, Loader2 } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import {
  ApiError,
  fetchPortfolioDetail,
  fetchPortfolios,
  type AIHoldingDetail,
  type AIPortfolio,
  type AIPortfolioDetail,
  type DataSourceInfo,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { SourceBadges } from "../../shared/ui/SourceBadges";

interface PortfolioHolding {
  symbol: string;
  company: string;
  sector: string;
  weight: number;
  returnPct: number;
  beta: number;
  pe: number;
  pb: number;
  volatility: number;
}

const CHART_COLORS = [
  "#0f86ba",
  "#20a6d5",
  "#13b3a1",
  "#4fa15d",
  "#e8a640",
  "#c66c41",
  "#8b7ad3",
  "#b262bb",
];

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
}

interface PortfolioViewProps {
  dataMode: "live" | "demo";
}

export function PortfolioView(props: PortfolioViewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [portfolios, setPortfolios] = useState<AIPortfolio[]>([]);
  const [activePortfolio, setActivePortfolio] = useState<AIPortfolioDetail | null>(null);
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [dataSources, setDataSources] = useState<DataSourceInfo[]>([]);

  const userId = useMemo(() => getUserId(), []);

  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchPortfolios(userId);
      setPortfolios(list);
      if (list.length > 0) {
        const primary = list.find((p) => p.is_primary) ?? list[0];
        const detail = await fetchPortfolioDetail(primary.id);
        setActivePortfolio(detail);
        setDataSources(detail.data_sources ?? []);
        const mapped: PortfolioHolding[] = (detail.holdings ?? []).map((h: AIHoldingDetail) => ({
          symbol: h.ticker_nse ?? h.company_id.slice(0, 6),
          company: h.company_name ?? "Unknown",
          sector: h.sector ?? "Unknown",
          weight: h.weight ?? 0,
          returnPct: h.return_pct ?? 0,
          beta: 1.0,
          pe: 0,
          pb: 0,
          volatility: 0,
        }));
        setHoldings(mapped);
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not load portfolio. Create one to get started."
      );
      setHoldings([]);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    void loadPortfolio();
  }, [loadPortfolio]);

  const totalWeight = useMemo(() => holdings.reduce((acc, h) => acc + h.weight, 0) || 100, [holdings]);

  const portfolioBeta = useMemo(
    () => {
      const backendBeta = activePortfolio?.metrics?.portfolio_beta as number | undefined;
      if (backendBeta != null) return backendBeta;
      return holdings.length
        ? holdings.reduce((acc, h) => acc + (h.beta * h.weight) / totalWeight, 0)
        : 1;
    },
    [holdings, totalWeight, activePortfolio]
  );

  const sharpeRatio = useMemo(
    () => (activePortfolio?.metrics?.sharpe_ratio as number | undefined) ?? null,
    [activePortfolio]
  );

  const portfolioVolatility = useMemo(
    () => (activePortfolio?.metrics?.portfolio_volatility as number | undefined) ?? null,
    [activePortfolio]
  );

  const diversificationScore = useMemo(
    () => (activePortfolio?.metrics?.diversification_score as number | undefined) ?? null,
    [activePortfolio]
  );

  const backendSectorAllocation = useMemo(() => {
    const alloc = activePortfolio?.metrics?.sector_allocation as Record<string, number> | undefined;
    if (alloc && Object.keys(alloc).length > 0) {
      return Object.entries(alloc)
        .map(([sector, weight]) => ({ sector, weight: weight * 100 }))
        .sort((a, b) => b.weight - a.weight);
    }
    return null;
  }, [activePortfolio]);

  const sectorWeights = useMemo(() => {
    const map = new Map<string, number>();
    for (const h of holdings) {
      map.set(h.sector, (map.get(h.sector) ?? 0) + h.weight);
    }
    return Array.from(map.entries())
      .map(([sector, weight]) => ({ sector, weight }))
      .sort((a, b) => b.weight - a.weight);
  }, [holdings]);

  const pieData = useMemo(
    () => sectorWeights.map((item) => ({ name: item.sector, value: Number(item.weight.toFixed(2)) })),
    [sectorWeights]
  );

  const maxSectorWeight = sectorWeights[0]?.weight ?? 1;

  if (loading) {
    return (
      <section className="page-wrap">
        <PageHeader
          title="Portfolio Intelligence"
          subtitle="Loading portfolio data..."
          dataMode={props.dataMode}
        />
        <div className="notice">
          <Loader2 size={16} className="spin" /> Loading your portfolio...
        </div>
      </section>
    );
  }

  return (
    <section className="page-wrap">
      <PageHeader
        title="Portfolio Intelligence"
        subtitle="Exposure, risk concentration, and opportunity signals from your broker portfolio."
        dataMode={props.dataMode}
        right={
          <button type="button" className="primary-btn" onClick={() => void loadPortfolio()}>
            Refresh Portfolio
          </button>
        }
      />

      {error ? <div className="notice warning">{error}</div> : null}

      <SourceBadges sources={dataSources} />

      {!holdings.length && !error ? (
        <div className="notice">
          No holdings found. Create a portfolio and add holdings via the API, or connect your
          Upstox/Kite broker account.
        </div>
      ) : null}

      <div className="kpi-grid portfolio-kpi-grid">
        <article className="kpi-card">
          <p>Portfolio Beta</p>
          <h2>{portfolioBeta.toFixed(2)}</h2>
          <small>Benchmark beta = 1.00</small>
        </article>
        <article className="kpi-card">
          <p>Sharpe Ratio</p>
          <h2>{sharpeRatio != null ? sharpeRatio.toFixed(2) : "—"}</h2>
          <small>Risk-adjusted return vs 7% G-Sec</small>
        </article>
        <article className="kpi-card">
          <p>Volatility (σ)</p>
          <h2>{portfolioVolatility != null ? `${(portfolioVolatility * 100).toFixed(1)}%` : "—"}</h2>
          <small>Annualised portfolio volatility</small>
        </article>
        <article className="kpi-card">
          <p>Diversification</p>
          <h2>{diversificationScore != null ? `${diversificationScore}/100` : `${holdings.length} holdings`}</h2>
          <small>{diversificationScore != null ? "HHI diversification score" : "Holdings count"}</small>
        </article>
      </div>

      {(backendSectorAllocation ?? sectorWeights).length > 0 && (
        <div className="split-grid portfolio-grid-extended">
          <article className="feature-card">
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>Sector Allocation</h3>
            </div>
            <div className="allocation-list">
              {(backendSectorAllocation ?? sectorWeights).map((sectorItem) => (
                <div key={sectorItem.sector} className="allocation-item">
                  <div className="allocation-meta">
                    <span>{sectorItem.sector}</span>
                    <span>{sectorItem.weight.toFixed(1)}%</span>
                  </div>
                  <div className="allocation-track">
                    <span
                      className="allocation-fill"
                      style={{ width: `${(sectorItem.weight / Math.max(...(backendSectorAllocation ?? sectorWeights).map(s => s.weight), 1)) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <Compass size={18} />
              <h3>Sector Donut</h3>
            </div>
            <div className="chart-wrap medium">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={54}
                    outerRadius={82}
                    stroke="none"
                  >
                    {pieData.map((entry, index) => (
                      <Cell
                        key={`${entry.name}-${index}`}
                        fill={CHART_COLORS[index % CHART_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => `${Number(value).toFixed(1)}%`}
                    labelFormatter={(label) => String(label)}
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid rgba(120,132,145,0.25)",
                      background: "rgba(12,18,26,0.92)",
                      color: "#e8edf2",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </article>
        </div>
      )}

      {holdings.length > 0 && (
        <div className="table-card">
          <div className="table-head">
            <h3>Top Holdings</h3>
            <span>From backend portfolio</span>
          </div>
          {holdings.map((holding) => (
            <div key={holding.symbol} className="table-row portfolio-row">
              <span>
                {holding.symbol}
                <small>{holding.company}</small>
              </span>
              <span>{holding.weight.toFixed(1)}%</span>
              <span className={holding.returnPct >= 0 ? "positive" : "negative"}>
                {holding.returnPct >= 0 ? "+" : ""}
                {holding.returnPct.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
