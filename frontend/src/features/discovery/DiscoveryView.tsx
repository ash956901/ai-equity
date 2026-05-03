import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Lightbulb, Search } from "lucide-react";

import {
  ApiError,
  fetchCompanies,
  fetchInsights,
  type AICompany,
  type InsightCard,
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

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  causal_cross_industry: "Causal cross-industry",
  supply_chain_ripple: "Supply-chain ripple",
  sentiment_driven: "Sentiment swing",
  event_catalyst: "Event catalyst",
  second_order: "Second-order",
};

function formatDirection(direction?: string | null): string {
  if (!direction) return "neutral";
  return direction;
}

function formatConfidence(value?: number | null): string {
  if (value === null || value === undefined) return "n/a";
  return `${Math.round(value * 100)}%`;
}

export function DiscoveryView(props: DiscoveryViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [query, setQuery] = useState("");
  const [activeSector, setActiveSector] = useState<string>("all");
  const [companies, setCompanies] = useState<AICompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [sectors, setSectors] = useState<string[]>(["all"]);

  const [insights, setInsights] = useState<InsightCard[]>([]);
  const [insightLoading, setInsightLoading] = useState(true);
  const [insightError, setInsightError] = useState<string | null>(null);
  const [insightFilter, setInsightFilter] = useState<string>("all");

  const loadCompanies = useCallback(async (searchTerm?: string, sector?: string) => {
    setLoading(true);
    setError(null);
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

  const loadInsights = useCallback(async (filter: string) => {
    setInsightLoading(true);
    setInsightError(null);
    try {
      const resp = await fetchInsights({
        insightType: filter === "all" ? undefined : filter,
        limit: 12,
        days: 7,
      });
      setInsights(resp.items);
    } catch (err) {
      setInsightError(err instanceof ApiError ? err.message : "Could not load insights.");
      setInsights([]);
    } finally {
      setInsightLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCompanies();
  }, [loadCompanies]);

  useEffect(() => {
    void loadInsights(insightFilter);
  }, [insightFilter, loadInsights]);

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
    const sectorParam = activeSector !== "all" ? activeSector : undefined;
    void loadCompanies(query.trim() || undefined, sectorParam);
  }, [activeSector, loadCompanies, query]);

  const formatMarketCap = (mcInr?: number) => {
    if (!mcInr) return "N/A";
    if (mcInr >= 1e12) return `\u20B9${(mcInr / 1e12).toFixed(1)}T`;
    if (mcInr >= 1e9) return `\u20B9${(mcInr / 1e9).toFixed(1)}B`;
    if (mcInr >= 1e7) return `\u20B9${(mcInr / 1e7).toFixed(0)}Cr`;
    return `\u20B9${mcInr.toLocaleString()}`;
  };

  const insightTypes = useMemo(
    () => ["all", ...Object.keys(INSIGHT_TYPE_LABELS)],
    []
  );

  return (
    <section className="page-wrap">
      <PageHeader
        title="Company Discovery"
        subtitle={`Explore the full NSE+BSE universe - ${totalCount.toLocaleString()} companies available.`}
        dataMode={props.dataMode}
      />

      <div className="discovery-panel" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Lightbulb size={16} />
          <h3 style={{ margin: 0 }}>Daily insight feed</h3>
          <span className="chip" style={{ marginLeft: "auto" }}>
            {insightLoading ? "Loading..." : `${insights.length} active`}
          </span>
        </div>

        <div className="discovery-controls" style={{ marginBottom: 12 }}>
          <select
            className="type-select"
            value={insightFilter}
            onChange={(e) => setInsightFilter(e.target.value)}
          >
            {insightTypes.map((t) => (
              <option key={t} value={t}>
                {t === "all" ? "All insight types" : INSIGHT_TYPE_LABELS[t] ?? t}
              </option>
            ))}
          </select>
        </div>

        {insightError ? <div className="notice warning">{insightError}</div> : null}

        <div className="discovery-grid">
          {!insightLoading && insights.length ? (
            insights.map((card) => (
              <article
                key={card.insight_id}
                className="discovery-card"
                style={{ borderLeft: "3px solid var(--accent, #6c8cff)" }}
              >
                <div className="discovery-card-head">
                  <div>
                    <p className="discovery-symbol" style={{ textTransform: "uppercase" }}>
                      {INSIGHT_TYPE_LABELS[card.insight_type] ?? card.insight_type}
                    </p>
                    <h3 style={{ marginTop: 4 }}>{card.headline}</h3>
                  </div>
                  <div className="discovery-card-actions">
                    <span className="chip">{formatDirection(card.predicted_direction)}</span>
                    <span className="chip">conf {formatConfidence(card.confidence)}</span>
                  </div>
                </div>

                <p className="discovery-insight" style={{ marginTop: 8 }}>
                  {card.narrative ?? ""}
                </p>

                {card.related_themes && card.related_themes.length ? (
                  <p className="discovery-sector" style={{ marginTop: 6 }}>
                    Themes: {card.related_themes.join(", ")}
                  </p>
                ) : null}
                {card.related_sectors && card.related_sectors.length ? (
                  <p className="discovery-sector" style={{ marginTop: 2 }}>
                    Sectors: {card.related_sectors.join(", ")}
                  </p>
                ) : null}
                {card.horizon_days ? (
                  <p className="discovery-sector" style={{ marginTop: 2 }}>
                    Horizon: {card.horizon_days}d
                  </p>
                ) : null}
              </article>
            ))
          ) : !insightLoading ? (
            <div className="list-item single-line">
              <p>No insight cards yet. Run the daily ETL to populate the feed.</p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="discovery-panel">
        <form
          className="search-pill discovery-search"
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
        >
          <Search size={14} />
          <input
            placeholder="Search by name, ticker, or ISIN..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </form>

        <div className="discovery-controls">
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
          <button type="button" className="secondary-btn mini-btn" onClick={handleSearch}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {error ? <div className="notice warning">{error}</div> : null}

      <div className="notice">
        {loading ? "Loading companies..." : `${companies.length} companies shown of ${totalCount} total.`}
      </div>

      <div className="discovery-grid">
        {!loading && companies.length ? (
          companies.map((company) => (
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
                        title: `${company.ticker_nse ?? ""} \u00B7 ${company.name}`,
                        subtitle: company.sector ?? "",
                      })
                    }
                  >
                    {props.isFavorited({
                      type: "company",
                      title: `${company.ticker_nse ?? ""} \u00B7 ${company.name}`,
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
        ) : !loading ? (
          <div className="list-item single-line">
            <p>No companies found. Try a different search term.</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
