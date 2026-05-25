import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { searchCompaniesDB } from "../api/platform";
import type { AICompany } from "../types/api";

interface CompanyOption {
  id: string;
  name: string;
  ticker: string;
  sector: string;
}

interface Props {
  placeholder?: string;
  onSelect: (company: CompanyOption) => void;
  initialValue?: string;
  className?: string;
}

export function CompanySearchInput({ placeholder = "Search companies…", onSelect, initialValue = "", className = "" }: Props) {
  const [input, setInput] = useState(initialValue);
  const [results, setResults] = useState<AICompany[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInput(initialValue);
  }, [initialValue]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleChange(value: string) {
    setInput(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await searchCompaniesDB(value, 8);
        setResults(data);
        setOpen(true);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
  }

  function handleSelect(company: AICompany) {
    const ticker = company.ticker_nse ?? company.ticker_bse ?? "";
    setInput(`${company.name} (${ticker || "—"})`);
    setOpen(false);
    setResults([]);
    onSelect({ id: company.id, name: company.name, ticker, sector: company.sector ?? "" });
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") setOpen(false);
  }

  function handleClear() {
    setInput("");
    setResults([]);
    setOpen(false);
  }

  const displayTicker = (c: AICompany) => c.ticker_nse ?? c.ticker_bse ?? "—";

  return (
    <div ref={containerRef} style={{ position: "relative" }} className={className}>
      <div className="search-pill" style={{ width: "100%" }}>
        <Search size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
        <input
          type="text"
          value={input}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder={placeholder}
          style={{
            border: 0,
            padding: 0,
            background: "transparent",
            flex: 1,
            color: "var(--ink)",
            fontSize: "0.875rem",
            outline: "none",
            minWidth: 0,
          }}
        />
        {loading && (
          <div
            style={{
              width: 14,
              height: 14,
              border: "2px solid var(--brand)",
              borderTopColor: "transparent",
              borderRadius: "50%",
              animation: "spin 0.7s linear infinite",
              flexShrink: 0,
            }}
          />
        )}
        {input && !loading && (
          <button
            type="button"
            className="favorite-icon-btn"
            onClick={handleClear}
            style={{ flexShrink: 0 }}
          >
            <X size={12} />
          </button>
        )}
      </div>

      {open && (
        <div
          style={{
            position: "absolute",
            zIndex: 50,
            width: "100%",
            marginTop: 4,
            background: "var(--bg-elevated)",
            border: "1px solid var(--line)",
            borderRadius: 10,
            boxShadow: "0 8px 24px rgba(0,0,0,0.18)",
            overflow: "hidden",
          }}
        >
          {results.length === 0 ? (
            <div style={{ padding: "10px 14px", fontSize: "0.82rem", color: "var(--muted)" }}>
              No results found
            </div>
          ) : (
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {results.map((company) => (
                <li
                  key={company.id}
                  onMouseDown={() => handleSelect(company)}
                  onMouseEnter={() => setHoveredId(company.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  style={{
                    padding: "9px 14px",
                    cursor: "pointer",
                    background: hoveredId === company.id ? "var(--bg)" : "transparent",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  <div style={{ fontSize: "0.875rem", color: "var(--ink)", fontWeight: 500 }}>
                    {company.name}{" "}
                    <span style={{ color: "var(--brand)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                      ({displayTicker(company)})
                    </span>
                  </div>
                  {company.sector && (
                    <div style={{ fontSize: "0.75rem", color: "var(--muted)", marginTop: 2 }}>
                      {company.sector}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
