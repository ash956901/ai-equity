import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import {
  compareCompanies,
  searchCompaniesDB,
  type CompareResponse,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";

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

function normalizeSymbolsInput(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 4)
    )
  );
}

export function ComparisonWorkspaceView(props: ComparisonWorkspaceViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [inputText, setInputText] = useState("RELIANCE, TCS");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>(["RELIANCE", "TCS"]);
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
      .slice(0, 4);

    if (normalized.length >= 2) {
      setSelectedSymbols(normalized);
      setInputText(normalized.join(", "));
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const [selectedCompanies, setSelectedCompanies] = useState<DiscoveryCompany[]>([]);

  useEffect(() => {
    if (!selectedSymbols.length) return;
    const companies = selectedSymbols.map(
      (symbol) =>
        ({
          symbol,
          name: symbol,
          sector: "Loading...",
          marketCapBn: 0,
          insight: "",
          themeScores: {},
        }) as DiscoveryCompany
    );
    setSelectedCompanies(companies);

    Promise.all(selectedSymbols.map((s) => searchCompaniesDB(s, 1)))
      .then((results) => {
        const enriched = results.map((r, i) => {
          const c = r[0];
          if (!c) return companies[i];
          return {
            symbol: c.ticker_nse ?? selectedSymbols[i],
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
  }, [selectedSymbols]);

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

  const applySymbols = () => {
    const deduped = normalizeSymbolsInput(inputText);
    if (deduped.length < 2) {
      return;
    }

    setSelectedSymbols(deduped);
    setInputText(deduped.join(", "));
    setCompareResult(null);
    setCompareError(null);
  };

  const runComparison = async () => {
    if (props.dataMode === "demo") {
      props.pushToast("Switch to Live API mode to run backend comparison.", "info");
      return;
    }

    const typedSymbols = normalizeSymbolsInput(inputText);
    const symbols = typedSymbols.length >= 2 ? typedSymbols : selectedSymbols;

    if (symbols.length < 2) {
      props.pushToast("Select at least two valid companies first", "warning");
      return;
    }

    const comparedSymbols = symbols.slice(0, 2);
    if (symbols.length > 2) {
      props.pushToast("Backend compare supports 2 companies. Using first two symbols.", "info");
    }

    const comparedNames = comparedSymbols.map((symbol) => {
      const matched = selectedCompanies.find((company) => company.symbol.toUpperCase() === symbol);
      return matched?.name ?? symbol;
    });

    setSelectedSymbols(comparedSymbols);
    setInputText(comparedSymbols.join(", "));
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
    const typedSymbols = normalizeSymbolsInput(inputText);
    const candidateSymbols = typedSymbols.length >= 2 ? typedSymbols : selectedSymbols;

    if (candidateSymbols.length < 2) {
      props.pushToast("Select at least two valid companies first", "warning");
      return;
    }

    const symbols = candidateSymbols;
    setSelectedSymbols(symbols);
    setInputText(symbols.join(", "));

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
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              applySymbols();
            }}
          >
            <Search size={14} />
            <input
              placeholder="RELIANCE, TCS, INFY"
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
            />
          </form>
        }
      />

      <div className="comparison-toolbar">
        <button type="button" className="primary-btn" onClick={applySymbols}>
          Apply Comparison
        </button>
        <button type="button" className="primary-btn" onClick={() => void runComparison()}>
          {compareLoading ? "Comparing..." : "Run Backend Compare"}
</button>
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
            if (!selectedSymbols.length) return;
            props.setSearchSelection({
              stamp: Date.now(),
              companySymbol: selectedSymbols[0],
            });
            props.goToView("company");
          }}
        >
          Open First Company
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
              <div className="score-box">
                <span className="score-box-label">Growth</span>
                <span className={`score-box-value ${compareResult.comparison.growth}`}>{compareResult.comparison.growth}</span>
              </div>
              <div className="score-box">
                <span className="score-box-label">Profitability</span>
                <span className={`score-box-value ${compareResult.comparison.profitability}`}>{compareResult.comparison.profitability}</span>
              </div>
              <div className="score-box">
                <span className="score-box-label">Risk</span>
                <span className={`score-box-value ${compareResult.comparison.risk}`}>{compareResult.comparison.risk}</span>
              </div>
              <div className="score-box">
                <span className="score-box-label">Valuation</span>
                <span className={`score-box-value ${compareResult.comparison.valuation}`}>{compareResult.comparison.valuation}</span>
              </div>
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
              <div className="detailed-card growth">
                <h4>Growth</h4>
                <p>{compareResult.detailed_comparison?.growth || "No growth details available."}</p>
              </div>
              <div className="detailed-card profitability">
                <h4>Profitability</h4>
                <p>{compareResult.detailed_comparison?.profitability || "No profitability details available."}</p>
              </div>
              <div className="detailed-card risk">
                <h4>Risk</h4>
                <p>{compareResult.detailed_comparison?.risk || "No risk details available."}</p>
              </div>
              <div className="detailed-card valuation">
                <h4>Valuation</h4>
                <p>{compareResult.detailed_comparison?.valuation || "No valuation details available."}</p>
              </div>
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
