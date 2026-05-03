import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Brain, Search, X } from "lucide-react";

import {
  ApiError,
  fetchCompanies,
  fetchThematicScreen,
  type AICompany,
  type ThematicResult,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { SourceBadges } from "../../shared/ui/SourceBadges";

interface SearchSelection {
  stamp: number;
  discoveryQuery?: string;
}

interface FavoriteItem {
  type: "company" | "filing" | "headline";
  symbol?: string;
  title: string;
  subtitle?: string;
}

interface DiscoveryViewProps {
  dataMode: "live" | "demo";
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: "company") => void;
  setSearchSelection: (selection: {
    stamp: number;
    companySymbol: string;
    companyId: string;
  }) => void;
}

export function DiscoveryView(props: DiscoveryViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [query, setQuery] = useState("");
  const [activeSector, setActiveSector] = useState<string>("all");
  const [companies, setCompanies] = useState<AICompany[]>([]);
  const [thematicResults, setThematicResults] = useState<ThematicResult[]>([]);
  const [mode, setMode] = useState<"keyword" | "thematic">("keyword");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [sectors, setSectors] = useState<string[]>(["all"]);

  const loadCompanies = useCallback(async (searchTerm?: string, sector?: string) => {
    setLoading(true);
    setError(null);
    setThematicResults([]);
    try {
      const sectorParam = sector && sector !== "all" ? sector : undefined;
      const resp = await fetchCompanies(50, 0, searchTerm, sectorParam);
      setCompanies(resp.companies);
      setTotalCount(resp.total);
      const sectorSet = new Set(resp.companies.map((c) => c.sector).filter(Boolean) as string[]);
      setSectors(["all", ...Array.from(sectorSet).sort()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load companies.");
      setCompanies([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const runThematicSearch = useCallback(async (q: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setCompanies([]);
    try {
      const results = await fetchThematicScreen(q.trim(), 20);
      setThematicResults(results);
      setTotalCount(results.length);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "AI thematic search failed.");
      setThematicResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCompanies();
  }, [loadCompanies]);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;
    if (props.searchSelection.discoveryQuery) {
      setQuery(props.searchSelection.discoveryQuery);
      void loadCompanies(props.searchSelection.discoveryQuery);
    }
    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, loadCompanies, props.searchSelection]);

  const handleSearch = useCallback(() => {
    if (mode === "thematic") {
      void runThematicSearch(query);
    } else {
      const sectorParam = activeSector !== "all" ? activeSector : undefined;
      void loadCompanies(query.trim() || undefined, sectorParam);
    }
  }, [activeSector, loadCompanies, query, mode, runThematicSearch]);

  const formatMarketCap = (mcInr?: number) => {
    if (!mcInr) return "N/A";
    if (mcInr >= 1e12) return `₹${(mcInr / 1e12).toFixed(1)}T`;
    if (mcInr >= 1e9) return `₹${(mcInr / 1e9).toFixed(1)}B`;
    if (mcInr >= 1e7) return `₹${(mcInr / 1e7).toFixed(0)}Cr`;
    return `₹${mcInr.toLocaleString()}`;
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Company Discovery"
        subtitle={
          mode === "thematic"
            ? "AI semantic discovery — find companies by investment theme using real filing data."
            : `Explore the full NSE+BSE universe - ${totalCount.toLocaleString()} companies available.`
        }
        dataMode={props.dataMode}
      />

      <div className="discovery-panel">
        {/* Mode toggle */}
        <div className="discovery-mode-toggle">
          <button
            type="button"
            className={`mode-pill ${mode === "keyword" ? "active" : ""}`}
            onClick={() => {
              setMode("keyword");
              setThematicResults([]);
              void loadCompanies();
            }}
          >
            <Search size={13} />
            Keyword Search
          </button>
          <button
            type="button"
            className={`mode-pill ${mode === "thematic" ? "active" : ""}`}
            onClick={() => {
              setMode("thematic");
              setCompanies([]);
            }}
          >
            <Brain size={13} />
            AI Thematic
          </button>
        </div>

        <form
          className="search-pill discovery-search"
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
        >
          <Search size={14} />
          <input
            placeholder={
              mode === "thematic"
                ? "e.g. renewable energy expansion, AI infrastructure, telecom regulatory risk..."
                : "Search by name, ticker, or ISIN..."
            }
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          {query && (
            <button
              type="button"
              className="favorite-icon-btn"
              onClick={() => {
                setQuery("");
                if (mode === "keyword") void loadCompanies();
                else setThematicResults([]);
              }}
            >
              <X size={12} />
            </button>
          )}
        </form>

        <div className="discovery-trending-themes" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: "var(--muted)", alignSelf: "center" }}>Trending:</span>
          {["AI Infrastructure", "Green Hydrogen", "Digital Banking", "EV Supply Chain", "Defense Systems"].map(theme => (
            <button
              key={theme}
              type="button"
              className="mini-chip-btn"
              onClick={() => {
                setQuery(theme);
                setMode("thematic");
                void runThematicSearch(theme);
              }}
              style={{
                fontSize: 11,
                padding: "4px 10px",
                borderRadius: 20,
                border: "1px solid var(--line)",
                background: "var(--bg-elevated)",
                cursor: "pointer",
                color: "var(--ink)"
              }}
            >
              {theme}
            </button>
          ))}
        </div>

        <div className="discovery-controls">

          {mode === "keyword" && (
            <select
              className="type-select"
              value={activeSector}
              onChange={(event) => {
                setActiveSector(event.target.value);
              }}
            >
              {sectors.map((sector) => (
                <option key={sector} value={sector}>
                  Sector: {sector === "all" ? "All" : sector}
                </option>
              ))}
            </select>
          )}
          <button type="button" className="secondary-btn mini-btn" onClick={handleSearch}>
            {loading ? "Searching..." : mode === "thematic" ? "Find Companies" : "Search"}
          </button>
        </div>
      </div>

      {error ? <div className="notice warning">{error}</div> : null}

      {mode === "thematic" && !loading && thematicResults.length === 0 && !error && (
        <div className="notice">
          Enter an investment theme above and click "Find Companies" to discover stocks using AI.
        </div>
      )}

      {mode === "keyword" && (
        <div className="notice">
          {loading ? "Loading companies..." : `${companies.length} companies shown of ${totalCount} total.`}
        </div>
      )}

      {/* Thematic Results */}
      {mode === "thematic" && thematicResults.length > 0 && (
        <div className="notice">
          {`${thematicResults.length} companies matched "${query}" via AI semantic search.`}
        </div>
      )}

      <div className="discovery-grid">
        {/* Keyword results */}
        {mode === "keyword" && !loading && companies.length
          ? companies.map((company) => (
              <article key={company.id} className="discovery-card">
                <div className="discovery-card-head">
                  <div>
                    <p className="discovery-symbol">{company.ticker_nse ?? company.ticker_bse ?? "-"}</p>
                    <h3>{company.name}</h3>
                  </div>
                  <div className="discovery-card-actions">
                    <span className="chip">{formatMarketCap(company.market_cap_inr)}</span>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      aria-label={`Save ${company.name} to favorites`}
                      onClick={() =>
                        props.addFavorite({
                          type: "company",
                          symbol: company.ticker_nse ?? company.id,
                          title: `${company.ticker_nse ?? ""} · ${company.name}`,
                          subtitle: company.sector ?? "",
                        })
                      }
                    >
                      {props.isFavorited({
                        type: "company",
                        title: `${company.ticker_nse ?? ""} · ${company.name}`,
                        symbol: company.ticker_nse ?? company.id,
                      }) ? (
                        <BookmarkCheck size={14} />
                      ) : (
                        <Bookmark size={14} />
                      )}
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      aria-label={`Open ${company.name} workspace`}
                      onClick={() => {
                        props.setSearchSelection({
                          stamp: Date.now(),
                          companySymbol: company.ticker_nse ?? company.ticker_bse ?? company.name,
                          companyId: company.id,
                        });
                        props.goToView("company");
                      }}
                    >
                      <ArrowUpRight size={14} />
                    </button>
                  </div>
                </div>

                <p className="discovery-sector">{company.sector ?? "Unknown sector"}</p>
                <p className="discovery-insight">{company.industry ?? company.description ?? ""}</p>

                <SourceBadges sources={company.data_sources} />

                <button
                  type="button"
                  className="secondary-btn mini-btn open-company-btn"
                  onClick={() => {
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: company.ticker_nse ?? company.ticker_bse ?? company.name,
                      companyId: company.id,
                    });
                    props.goToView("company");
                  }}
                >
                  Open Company
                </button>
              </article>
            ))
          : null}

        {/* Thematic AI results */}
        {mode === "thematic" && thematicResults.map((result) => (
          <article key={result.company_id} className="discovery-card thematic-card">
            <div className="discovery-card-head">
              <div>
                <p className="discovery-symbol">{result.ticker_nse ?? result.ticker_bse ?? "—"}</p>
                <h3>{result.company_name}</h3>
              </div>
              <div className="discovery-card-actions">
                <span className="chip thematic-score-chip">
                  {(result.relevance_score * 100).toFixed(0)}% match
                </span>
                <button
                  type="button"
                  className="favorite-icon-btn"
                  aria-label={`Open ${result.company_name} workspace`}
                  onClick={() => {
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: result.ticker_nse ?? result.ticker_bse ?? result.company_name,
                      companyId: result.company_id,
                    });
                    props.goToView("company");
                  }}
                >
                  <ArrowUpRight size={14} />
                </button>
              </div>
            </div>

            <p className="discovery-sector">
              {result.sector ?? "Unknown"}{result.industry ? ` · ${result.industry}` : ""}
            </p>

            <div className="thematic-meta">
              <span className="chip">{result.match_count} filing match{result.match_count !== 1 ? "es" : ""}</span>
              {result.market_cap_inr && (
                <span className="chip">{formatMarketCap(result.market_cap_inr)}</span>
              )}
            </div>

            {result.evidence_snippets.length > 0 && (
              <div className="thematic-evidence">
                <p className="thematic-evidence-label">Evidence from filings:</p>
                {result.evidence_snippets.slice(0, 2).map((snippet, i) => (
                  <p key={`ev-${result.company_id}-${i}`} className="thematic-evidence-text">
                    "{snippet.slice(0, 140)}{snippet.length > 140 ? "…" : ""}"
                  </p>
                ))}
              </div>
            )}

            <button
              type="button"
              className="secondary-btn mini-btn open-company-btn"
              onClick={() => {
                props.setSearchSelection({
                  stamp: Date.now(),
                  companySymbol: result.ticker_nse ?? result.ticker_bse ?? result.company_name,
                  companyId: result.company_id,
                });
                props.goToView("company");
              }}
            >
              Open Company
            </button>
          </article>
        ))}

        {!loading && mode === "keyword" && companies.length === 0 ? (
          <div className="list-item single-line">
            <p>No companies found. Try a different search term.</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
