import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Search } from "lucide-react";

import { ApiError, fetchCompanies, type AICompany } from "../../lib/api";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [sectors, setSectors] = useState<string[]>(["all"]);

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
    const sectorParam = activeSector !== "all" ? activeSector : undefined;
    void loadCompanies(query.trim() || undefined, sectorParam);
  }, [activeSector, loadCompanies, query]);

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
        subtitle={`Explore the full NSE+BSE universe - ${totalCount.toLocaleString()} companies available.`}
        dataMode={props.dataMode}
      />

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
        ) : !loading ? (
          <div className="list-item single-line">
            <p>No companies found. Try a different search term.</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
