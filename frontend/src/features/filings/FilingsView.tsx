import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Bookmark, BookmarkCheck, Search } from "lucide-react";

import {
  ApiError,
  fetchSecFilings,
  searchCompanies,
  type CompanySearchResult,
  type SecFiling,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";

const DEMO_BANNER_MSG = "Demo mode — showing cached data. Switch to Live API for real-time results.";

interface SearchSelection {
  stamp: number;
  filingsSymbol?: string;
}

interface FavoriteItem {
  type: "company" | "filing" | "headline";
  symbol?: string;
  title: string;
  subtitle?: string;
}

interface FilingsViewProps {
  searchSelection: SearchSelection | null;
  dataMode: "live" | "demo";
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt"> & { url?: string }) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: "company") => void;
  setSearchSelection: (selection: { stamp: number; companySymbol: string; filingsSymbol: string }) => void;
}

export function FilingsView(props: FilingsViewProps) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [symbolInput, setSymbolInput] = useState("RELIANCE");
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");
  const [filingType, setFilingType] = useState("");

  const [filings, setFilings] = useState<SecFiling[]>([]);
  const [searchResults, setSearchResults] = useState<CompanySearchResult[]>([]);

  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadFilings = useCallback(
    async (symbol: string, selectedType?: string) => {
      setLoading(true);
      setError(null);

      if (props.dataMode === "demo") {
        setFilings([]);
        setError(DEMO_BANNER_MSG);
        setLoading(false);
        return;
      }

      try {
        const data = await fetchSecFilings(symbol, 12, selectedType);
        setFilings(data);
      } catch (loadError) {
        if (loadError instanceof ApiError && loadError.status === 401) {
          setError("Filings API is unauthorized (401) until backend key is configured.");
        } else {
          setError(`Could not load filings for ${symbol}.`);
        }
        setFilings([]);
      } finally {
        setLoading(false);
      }
    },
    [props.dataMode]
  );

  useEffect(() => {
    void loadFilings(activeSymbol, filingType || undefined);
  }, [activeSymbol, filingType, loadFilings]);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.filingsSymbol) {
      const normalized = props.searchSelection.filingsSymbol.toUpperCase();
      setActiveSymbol(normalized);
      setSymbolInput(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const handleSearch = useCallback(async () => {
    const query = symbolInput.trim();
    if (!query) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    setSearchError(null);

    if (props.dataMode === "demo") {
      setSearchResults([]);
      setSearchError(DEMO_BANNER_MSG);
      setSearchLoading(false);
      return;
    }

    try {
      const results = await searchCompanies(query, 6);
      setSearchResults(results);
    } catch (searchErr) {
      if (searchErr instanceof ApiError && searchErr.status === 401) {
        setSearchError("Company search is unauthorized (401) right now.");
      } else {
        setSearchError("Could not search companies right now.");
      }
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, [props.dataMode, symbolInput]);

  const applySymbol = useCallback((symbol?: string) => {
    if (!symbol) return;
    const normalized = symbol.toUpperCase();
    setActiveSymbol(normalized);
    setSymbolInput(normalized);
  }, []);

  const formatFilingDate = (value?: string) => {
    if (!value) return "Unknown date";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleDateString();
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Filings Tracker"
        subtitle="Review latest results, corporate updates, and disclosure trends."
        dataMode={props.dataMode}
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              applySymbol(symbolInput.trim());
            }}
          >
            <Search size={14} />
            <input
              placeholder="Search ticker"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
            />
          </form>
        }
      />

      <div className="news-toolbar">
        <div className="chip-row">
          <span className="chip">Active Symbol: {activeSymbol}</span>
          <span className="chip">Filings: {loading ? "--" : filings.length}</span>
        </div>
        <div className="chip-row">
          <select
            className="type-select"
            value={filingType}
            onChange={(event) => setFilingType(event.target.value)}
          >
            <option value="">All Types</option>
            <option value="Annual Report">Annual Report</option>
            <option value="Investor Presentation">Investor Presentation</option>
            <option value="Regulatory">Regulatory</option>
            <option value="Transcript">Transcript</option>
            <option value="Update">Update</option>
          </select>
          <button type="button" className="secondary-btn mini-btn" onClick={() => void handleSearch()}>
            {searchLoading ? "Searching..." : "Search Companies"}
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => void loadFilings(activeSymbol, filingType || undefined)}
          >
            Refresh Filings
          </button>
        </div>
      </div>

      {error ? <div className="notice warning">{error}</div> : null}
      {searchError ? <div className="notice warning">{searchError}</div> : null}

      {searchResults.length ? (
        <div className="search-results-card">
          <p className="results-title">Company Matches</p>
          <div className="chip-row">
            {searchResults.map((result, index) => (
              <button
                type="button"
                key={`${result.symbol ?? result.name ?? index}`}
                className="chip pick-chip"
                onClick={() => applySymbol(result.symbol)}
              >
                {(result.symbol ?? "N/A") + " · " + (result.name ?? "Unknown")}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="list-card">
        {loading ? (
          <div className="list-item single-line">
            <p>Loading filings...</p>
          </div>
        ) : null}

        {!loading && !filings.length ? (
          <div className="list-item single-line">
            <p>No filings found for {activeSymbol}.</p>
          </div>
        ) : null}

        {!loading
          ? filings.map((filing, index) => (
              <a
                key={`${filing.url ?? filing.finalLink ?? index}`}
                href={filing.finalLink ?? filing.url ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="list-item filing-item"
              >
                <div className="filing-content-wrap">
                  <p>{(filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`)}</p>
                  <span>{formatFilingDate(filing.filingDate ?? filing.acceptedDate)}</span>
                </div>
                <button
                  type="button"
                  className="favorite-icon-btn"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    props.addFavorite({
                      type: "filing",
                      symbol: activeSymbol,
                      title: (filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`),
                      subtitle: formatFilingDate(filing.filingDate ?? filing.acceptedDate),
                      url: filing.finalLink ?? filing.url,
                    });
                  }}
                  aria-label="Save filing to favorites"
                >
                  {props.isFavorited({
                    type: "filing",
                    symbol: activeSymbol,
                    title: (filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`),
                  }) ? (
                    <BookmarkCheck size={14} />
                  ) : (
                    <Bookmark size={14} />
                  )}
                </button>
                <button
                  type="button"
                  className="favorite-icon-btn"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: activeSymbol,
                      filingsSymbol: activeSymbol,
                    });
                    props.goToView("company");
                  }}
                  aria-label="Open company workspace"
                >
                  <ArrowUpRight size={14} />
                </button>
              </a>
            ))
          : null}
      </div>
    </section>
  );
}
