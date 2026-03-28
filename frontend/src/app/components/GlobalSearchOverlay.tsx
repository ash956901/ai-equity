import type { Dispatch, RefObject, SetStateAction } from "react";
import { Search } from "lucide-react";
import type { GlobalSearchResult } from "../types";

interface GlobalSearchOverlayProps {
  open: boolean;
  query: string;
  activeIndex: number;
  results: GlobalSearchResult[];
  inputRef: RefObject<HTMLInputElement | null>;
  setQuery: (value: string) => void;
  setActiveIndex: Dispatch<SetStateAction<number>>;
  onClose: () => void;
}

export function GlobalSearchOverlay(props: GlobalSearchOverlayProps) {
  if (!props.open) return null;

  return (
    <div className="global-search-overlay" role="dialog" aria-modal="true" aria-label="Global search">
      <button type="button" className="global-search-backdrop" onClick={props.onClose} />

      <div className="global-search-panel">
        <div className="global-search-head">
          <p className="results-title">Global Search</p>
          <span className="chip">Search company, theme, event, or query</span>
        </div>

        <div className="command-input-row">
          <Search size={15} />
          <input
            ref={props.inputRef}
            value={props.query}
            onChange={(event) => props.setQuery(event.target.value)}
            placeholder="Try: RELIANCE, defense, AI, risk..."
          />
        </div>

        <div className="global-search-results">
          {props.results.length ? (
            props.results.map((result, index) => (
              <button
                type="button"
                key={result.id}
                className={`global-search-item ${index === props.activeIndex ? "active" : ""}`}
                onMouseEnter={() => props.setActiveIndex(index)}
                onClick={result.onSelect}
              >
                <div>
                  <p>{result.title}</p>
                  <span>{result.subtitle}</span>
                </div>
                <span className={`chip global-search-type ${result.type}`}>{result.type}</span>
              </button>
            ))
          ) : (
            <p className="command-empty">No matches found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
