import { useEffect, useMemo, useState } from "react";

import {
  compareCompanies,
  searchCompaniesDB,
  type CompareResponse,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { CompanySearchInput } from "../../shared/components/CompanySearchInput";

type DataMode = "live" | "demo";
type ToastTone = "info" | "success" | "warning";

interface DiscoveryCompany {
  symbol: string;
  name: string;
  sector: string;
  marketCapBn: number;
  insight: string;
  themeScores: Record<string, number>;
}

interface ComparisonSearchSelection {
  stamp: number;
  compareSymbols?: string[];
}

interface ComparisonSelectionUpdate {
  stamp: number;
  reportScope?: "comparison";
  reportCompareSymbols?: string[];
  compareSymbols?: string[];
  companySymbol?: string;
}

interface ComparisonWorkspaceViewProps {
  dataMode: DataMode;
  pushToast: (message: string, tone?: ToastTone) => void;
  searchSelection: ComparisonSearchSelection | null;
  goToView: (view: "company") => void;
  setSearchSelection: (selection: ComparisonSelectionUpdate) => void;
}


interface CompanySelection {
  id: string;
  name: string;
  ticker: string;
  sector: string;
}

export function ComparisonWorkspaceView(props: ComparisonWorkspaceViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [companyA, setCompanyA] = useState<CompanySelection | null>(null);
  const [companyB, setCompanyB] = useState<CompanySelection | null>(null);
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [compareLoading, setCompareLoading] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const [compareError, setCompareError] = useState<string | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);

  useEffect(() => {
    if (!props.searchSelection?.compareSymbols?.length) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    const normalized = props.searchSelection.compareSymbols
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean)
      .slice(0, 2);

    if (normalized.length >= 2) {
      setSelectedSymbols(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const [selectedCompanies, setSelectedCompanies] = useState<DiscoveryCompany[]>([]);

  useEffect(() => {
    const symbols = companyA && companyB
      ? [companyA.ticker || companyA.name, companyB.ticker || companyB.name]
      : selectedSymbols;

    if (!symbols.length) return;

    const companies: DiscoveryCompany[] = companyA && companyB
      ? [
          { symbol: companyA.ticker || companyA.name, name: companyA.name, sector: companyA.sector || "…", marketCapBn: 0, insight: "", themeScores: {} },
          { symbol: companyB.ticker || companyB.name, name: companyB.name, sector: companyB.sector || "…", marketCapBn: 0, insight: "", themeScores: {} },
        ]
      : symbols.map((s) => ({ symbol: s, name: s, sector: "Loading…", marketCapBn: 0, insight: "", themeScores: {} }));

    setSelectedCompanies(companies);

    if (!companyA || !companyB) {
      Promise.all(symbols.map((s) => searchCompaniesDB(s, 1)))
        .then((results) => {
          const enriched = results.map((r, i) => {
            const c = r[0];
            if (!c) return companies[i];
            return {
              symbol: c.ticker_nse ?? symbols[i],
              name: c.name,
              sector: c.sector ?? "Unknown",
              marketCapBn: c.market_cap_inr ? c.market_cap_inr / 1e9 : 0,
              insight: c.industry ?? c.description ?? "",
              themeScores: {},
            } as DiscoveryCompany;
          });
          setSelectedCompanies(enriched);
        })
        .catch(() => {});
    }
  }, [companyA, companyB, selectedSymbols]);

  const allThemes = useMemo(() => {
    const set = new Set<string>();
    for (const company of selectedCompanies) {
      Object.keys(company.themeScores).forEach((theme) => set.add(theme));
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [selectedCompanies]);

  const comparisonRows = useMemo(() => {
    const rows = allThemes.map((theme) => {
      const values = selectedCompanies.map((company) => company.themeScores[theme] ?? 0);
      const max = Math.max(...values, 0);
      return { theme, values, max };
    });
    return rows;
  }, [allThemes, selectedCompanies]);

  const strongestSymbol = useMemo(() => {
    if (!selectedCompanies.length) return null;

    let best: { symbol: string; score: number } | null = null;
    for (const company of selectedCompanies) {
      const score = Math.max(...Object.values(company.themeScores), 0);
      if (!best || score > best.score) {
        best = { symbol: company.symbol, score };
      }
    }
    return best;
  }, [selectedCompanies]);

  const runComparison = async () => {
    if (!companyA || !companyB) {
      props.pushToast("Select both Company A and Company B first", "warning");
      return;
    }

    const comparedNames = [companyA.name, companyB.name];
    const comparedSymbols = [companyA.ticker || companyA.name, companyB.ticker || companyB.name];
    setSelectedSymbols(comparedSymbols);
    setCompareLoading(true);
    setCompareError(null);

    const userId =
      localStorage.getItem("equityai-user-id") ?? "11111111-1111-1111-1111-111111111111";

    try {
      const result = await compareCompanies({
        user_id: userId,
        company_names: comparedNames,
        expertise_level: "intermediate",
      });
      setCompareResult(result);
      props.pushToast("Comparison completed", "success");
    } catch {
      setCompareResult(null);
      setCompareError("Could not fetch comparison result right now.");
      props.pushToast("Comparison failed", "warning");
    } finally {
      setCompareLoading(false);
    }
  };

  const openComparisonReport = () => {
    const symbols = companyA && companyB
      ? [companyA.ticker || companyA.name, companyB.ticker || companyB.name]
      : selectedSymbols;

    if (symbols.length < 2) {
      props.pushToast("Select at least two valid companies first", "warning");
      return;
    }

    props.setSearchSelection({
      stamp: Date.now(),
      reportScope: "comparison",
      reportCompareSymbols: symbols,
      compareSymbols: symbols,
      companySymbol: symbols[0],
    });
    props.goToView("company");
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Comparison Workspace"
        subtitle="Compare companies side-by-side across themes, sector context, and qualitative signals."
        dataMode={props.dataMode}
      />

      <div className="comparison-search-row" style={{ display: "flex", gap: "12px", alignItems: "flex-end", marginBottom: "16px", flexWrap: "wrap" }}>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <label style={{ display: "block", fontSize: "0.75rem", color: "var(--muted)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Company A</label>
          <CompanySearchInput
            placeholder="Search company A…"
            onSelect={(c) => { setCompanyA(c); setCompareResult(null); setCompareError(null); }}
            initialValue={companyA ? `${companyA.name} (${companyA.ticker || "—"})` : ""}
          />
        </div>
        <div style={{ flex: 1, minWidth: "220px" }}>
          <label style={{ display: "block", fontSize: "0.75rem", color: "var(--muted)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>Company B</label>
          <CompanySearchInput
            placeholder="Search company B…"
            onSelect={(c) => { setCompanyB(c); setCompareResult(null); setCompareError(null); }}
            initialValue={companyB ? `${companyB.name} (${companyB.ticker || "—"})` : ""}
          />
        </div>
        <button type="button" className="primary-btn" onClick={() => void runComparison()} disabled={compareLoading || !companyA || !companyB}>
          {compareLoading ? "Comparing…" : "Compare"}
        </button>
      </div>

      <div className="comparison-toolbar">
        <button type="button" className="secondary-btn" onClick={() => setShowRaw(!showRaw)}>
          {showRaw ? "Hide raw response" : "Show raw response"}
        </button>
        <button type="button" className="primary-btn" onClick={openComparisonReport}>
          Generate Comparison Report
        </button>
        <button
          type="button"
          className="secondary-btn mini-btn"
          onClick={() => {
            if (!companyA) return;
            props.setSearchSelection({
              stamp: Date.now(),
              companySymbol: companyA.ticker || companyA.name,
            });
            props.goToView("company");
          }}
        >
          Open Company A
        </button>
      </div>

      <div className="notice">
        {strongestSymbol
          ? `Strongest theme momentum: ${strongestSymbol.symbol} (${strongestSymbol.score}/100 top signal).`
          : "Add at least two valid symbols from discovery dataset to compare."}
      </div>

      {compareError ? <div className="notice warning">{compareError}</div> : null}

      {compareResult && (
        <>
          <article className="terminal-panel">
            <h3 className="terminal-panel-title">Institutional Comparison Verdict</h3>

            <div className="verdict-banner">
              <h3>Final Verdict</h3>
              <p>{compareResult.final_verdict}</p>
            </div>

            <div className="comparison-scores">
              {(["growth", "profitability", "risk", "valuation"] as const).map((key) => {
                const winner = compareResult.comparison[key];
                const nameA = companyA?.name ?? "Company A";
                const nameB = companyB?.name ?? "Company B";
                const label = key.charAt(0).toUpperCase() + key.slice(1);
                return (
                  <div key={key} className="score-box">
                    <span className="score-box-label">{label}</span>
                    <span className={`score-box-value ${winner}`}>
                      {winner === "Tie" ? "Tie" : winner === "A" ? `🏆 ${nameA}` : `🏆 ${nameB}`}
                    </span>
                  </div>
                );
              })}
            </div>

            {compareResult.companyA_stock_data && compareResult.companyB_stock_data && (() => {
              const a = compareResult.companyA_stock_data as any;
              const b = compareResult.companyB_stock_data as any;
              const rows = [
                { label: 'CEO', key: 'ceo' },
                { label: 'Sector', key: 'sector' },
                { label: 'Domain', key: 'domain' },
                { label: 'Market Cap', key: 'market_cap', fmt: (v: any) => v != null ? `₹${(Number(v) / 1e7).toFixed(2)}Cr` : 'N/A' },
                { label: 'Net Profit', key: 'net_profit', fmt: (v: any) => v != null ? `₹${(Number(v) / 1e7).toFixed(2)}Cr` : 'N/A' },
                { label: 'Profit Margin', key: 'profit_margin', fmt: (v: any) => v != null ? `${Number(v).toFixed(2)}%` : 'N/A' },
                { label: 'Margin Trend', key: 'margin_trend' },
                { label: 'ROE', key: 'roe', fmt: (v: any) => v != null ? `${Number(v).toFixed(2)}%` : 'N/A' },
                { label: 'ROCE', key: 'roce', fmt: (v: any) => v != null ? `${Number(v).toFixed(2)}%` : 'N/A' },
                { label: 'P/E Ratio', key: 'pe_ratio', fmt: (v: any) => v != null ? Number(v).toFixed(2) : 'N/A' },
                { label: 'Debt/Equity', key: 'debt_to_equity', fmt: (v: any) => v != null ? Number(v).toFixed(2) : 'N/A' },
                { label: 'Rev Growth Score', key: 'revenue_growth_score', fmt: (v: any) => v != null ? Number(v).toFixed(2) : 'N/A' },
                { label: 'Qtr Consistency', key: 'quarterly_consistency', fmt: (v: any) => v != null ? Number(v).toFixed(2) : 'N/A' },
                { label: 'Earn Volatility', key: 'earnings_volatility', fmt: (v: any) => v != null ? Number(v).toFixed(2) : 'N/A' },
                { label: 'Data Source', key: 'data_source' },
              ];
              return (
                <div className="terminal-grid">
                  <div className="terminal-row header">
                    <div className="terminal-cell">Metric</div>
                    <div className="terminal-cell">{a.company_name ?? 'Company A'} ({a.ticker_nse ?? a.ticker_bse})</div>
                    <div className="terminal-cell">{b.company_name ?? 'Company B'} ({b.ticker_nse ?? b.ticker_bse})</div>
                  </div>
                  {rows.map((row) => (
                    <div key={row.key} className="terminal-row">
                      <div className="terminal-cell metric-name">{row.label}</div>
                      <div className="terminal-cell value">{row.fmt ? row.fmt(a[row.key]) : String(a[row.key] ?? 'N/A')}</div>
                      <div className="terminal-cell value">{row.fmt ? row.fmt(b[row.key]) : String(b[row.key] ?? 'N/A')}</div>
                    </div>
                  ))}
                </div>
              );
            })()}
            <div className="detailed-grid">
              {(["growth", "profitability", "risk", "valuation"] as const).map((key) => {
                const winner = compareResult.comparison[key];
                const nameA = companyA?.name ?? "Company A";
                const nameB = companyB?.name ?? "Company B";
                const label = key.charAt(0).toUpperCase() + key.slice(1);
                const aWins = winner === "A";
                const bWins = winner === "B";
                const isTie = winner === "Tie";
                return (
                  <div key={key} className={`detailed-card ${key}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, gap: 8, flexWrap: "wrap" }}>
                      <h4 style={{ margin: 0 }}>{label}</h4>
                      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                        <span style={{
                          fontSize: "0.72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 20,
                          background: aWins ? "color-mix(in srgb, var(--brand) 18%, transparent)" : isTie ? "color-mix(in srgb, var(--muted) 12%, transparent)" : "transparent",
                          color: aWins ? "var(--brand)" : "var(--muted)",
                          border: `1px solid ${aWins ? "color-mix(in srgb, var(--brand) 35%, transparent)" : "var(--line)"}`,
                          opacity: bWins ? 0.4 : 1,
                          whiteSpace: "nowrap",
                        }}>
                          {aWins ? "🏆 " : ""}{nameA}
                        </span>
                        <span style={{ fontSize: "0.68rem", color: "var(--muted)", fontWeight: 600 }}>vs</span>
                        <span style={{
                          fontSize: "0.72rem", fontWeight: 700, padding: "3px 10px", borderRadius: 20,
                          background: bWins ? "color-mix(in srgb, var(--good) 18%, transparent)" : isTie ? "color-mix(in srgb, var(--muted) 12%, transparent)" : "transparent",
                          color: bWins ? "var(--good)" : "var(--muted)",
                          border: `1px solid ${bWins ? "color-mix(in srgb, var(--good) 35%, transparent)" : "var(--line)"}`,
                          opacity: aWins ? 0.4 : 1,
                          whiteSpace: "nowrap",
                        }}>
                          {bWins ? "🏆 " : ""}{nameB}
                        </span>
                        {isTie && <span className="winner-badge tie">TIE</span>}
                      </div>
                    </div>
                    <p>{compareResult.detailed_comparison?.[key] || `No ${label.toLowerCase()} details available.`}</p>
                  </div>
                );
              })}
            </div>

            {compareResult.insights.length ? (
              <div className="compare-insights-list">
                <h4>Analyst Insights</h4>
                {compareResult.insights.map((insight, index) => (
                  <div key={`compare-insight-${index}`} className="insight-item">
                    <span className="insight-bullet" />
                    <p>{insight}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </article>          {showRaw && (
            <pre className="bg-gray-100 p-4 rounded overflow-x-auto mt-2">
              {JSON.stringify(compareResult, null, 2)}
            </pre>
          )}
        </>
      )}

      {selectedCompanies.length >= 2 ? (
        <div className="comparison-table-card">
          <div className="comparison-table-head">
            <span>Theme</span>
            {selectedCompanies.map((company) => (
              <span key={`head-${company.symbol}`}>{company.symbol}</span>
            ))}
          </div>

          {comparisonRows.map((row) => (
            <div key={row.theme} className="comparison-row">
              <span className="comparison-theme">{row.theme}</span>
              {row.values.map((value, index) => (
                <span
                  key={`${row.theme}-${selectedCompanies[index].symbol}`}
                  className={`comparison-value ${value === row.max ? "leading" : ""}`}
                >
                  {value}
                </span>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="list-item single-line">
          <p>Please enter at least two valid symbols (example: RELIANCE, TCS).</p>
        </div>
      )}

      <div className="comparison-cards-grid">
        {selectedCompanies.map((company) => (
          <article key={`card-${company.symbol}`} className="discovery-card">
            <div className="discovery-card-head">
              <div>
                <p className="discovery-symbol">{company.symbol}</p>
                <h3>{company.name}</h3>
              </div>
              <span className="chip">{company.sector}</span>
            </div>
            <p className="discovery-insight">{company.insight}</p>
            <div className="chip-row discovery-chips">
              {Object.entries(company.themeScores)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 4)
                .map(([theme, score]) => (
                  <span key={`${company.symbol}-${theme}`} className="chip discovery-theme-chip">
                    {theme} · {score}
                  </span>
                ))}
            </div>
</article>
        ))}
      </div>
    </section>
  );
}
