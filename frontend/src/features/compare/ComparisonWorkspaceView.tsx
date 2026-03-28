import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { searchCompaniesDB } from "../../lib/api";
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
