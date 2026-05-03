import { Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchHomePersonalized, type HomeCompany } from "../shared/api/home";
import { searchCompaniesDB } from "../lib/api";

interface OmniSearchProps {
  onPick: (ticker: string, companyId?: string) => void;
  placeholder?: string;
}

interface SearchHit {
  ticker: string;
  name: string;
  company_id?: string;
  sector?: string | null;
}

function fromHomeCompany(c: HomeCompany): SearchHit {
  return {
    ticker: c.ticker_nse || c.ticker_bse || "",
    name: c.name,
    company_id: c.company_id,
    sector: c.sector,
  };
}

export function OmniSearch({ onPick, placeholder = "Search companies, themes, tickers…" }: OmniSearchProps) {
  const [query, setQuery] = useState("");
  const [defaults, setDefaults] = useState<SearchHit[]>([]);
  const [results, setResults] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    fetchHomePersonalized()
      .then((d) => {
        const merged: SearchHit[] = [];
        const seen = new Set<string>();
        for (const c of [...d.watchlist_companies, ...d.holdings_companies]) {
          const hit = fromHomeCompany(c);
          if (!hit.ticker || seen.has(hit.ticker)) continue;
          seen.add(hit.ticker);
          merged.push(hit);
        }
        setDefaults(merged);
      })
      .catch(() => setDefaults([]));
  }, []);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    if (debounceRef.current !== null) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(async () => {
      try {
        const rows = await searchCompaniesDB(query.trim(), 10);
        setResults(
          rows.map((r) => ({
            ticker: r.symbol || r.ticker_nse || r.ticker_bse || r.name,
            name: r.name,
            company_id: r.id,
            sector: r.sector,
          })),
        );
      } catch {
        setResults([]);
      }
    }, 200);
    return () => {
      if (debounceRef.current !== null) window.clearTimeout(debounceRef.current);
    };
  }, [query]);

  const display: SearchHit[] = useMemo(
    () => (query.trim() ? results : defaults),
    [query, results, defaults],
  );

  return (
    <div className="omnisearch" onBlur={(e) => {
      // close only when focus actually leaves the panel
      if (!e.currentTarget.contains(e.relatedTarget as Node)) setOpen(false);
    }}>
      <div className="omnisearch__field">
        <Search size={14} />
        <input
          type="search"
          value={query}
          placeholder={placeholder}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
        />
      </div>
      {open && display.length > 0 ? (
        <ul className="omnisearch__results" role="listbox">
          {!query.trim() ? (
            <li className="omnisearch__heading">Your tracked companies</li>
          ) : null}
          {display.map((hit) => (
            <li key={`${hit.ticker}-${hit.company_id ?? "?"}`}>
              <button
                type="button"
                onClick={() => {
                  onPick(hit.ticker, hit.company_id);
                  setOpen(false);
                  setQuery("");
                }}
              >
                <strong>{hit.name}</strong>
                <span className="muted"> {hit.ticker}</span>
                <span className="muted"> · {hit.sector || ""}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
