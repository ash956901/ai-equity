import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";

import { fetchQuote, type QuotePayload } from "../../../shared/api/quotes";

interface QuoteHeaderProps {
  ticker: string;
  pollMs?: number;
  onCompanyResolved?: (companyId: string | null, name: string | null) => void;
}

function fmtINR(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `₹${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

export function QuoteHeader({
  ticker,
  pollMs = 10000,
  onCompanyResolved,
}: QuoteHeaderProps) {
  const { data: quote, error } = useQuery<QuotePayload>({
    queryKey: ["quote", ticker],
    queryFn: () => fetchQuote(ticker),
    refetchInterval: pollMs,
    refetchIntervalInBackground: false,
    staleTime: pollMs / 2,
  });

  useEffect(() => {
    if (quote) {
      onCompanyResolved?.(quote.company_id ?? null, quote.name ?? null);
    }
  }, [quote, onCompanyResolved]);

  const tone = useMemo(() => {
    const c = quote?.change_pct ?? 0;
    if (c > 0) return "up";
    if (c < 0) return "down";
    return "flat";
  }, [quote?.change_pct]);

  const errorMsg = quote?.error || (error ? "Could not load quote" : null);

  return (
    <header className={`quote-header quote-header--${tone}`}>
      <div className="quote-header__primary">
        <h2>{quote?.name || ticker.toUpperCase()}</h2>
        <span className="quote-header__symbol">
          {quote?.ticker || ticker.toUpperCase()} · {quote?.exchange || "NSE"}
        </span>
      </div>
      <div className="quote-header__price">
        <strong>{fmtINR(quote?.last_price ?? null)}</strong>
        <span>{fmtPct(quote?.change_pct ?? null)}</span>
      </div>
      <div className="quote-header__strip">
        <Stat label="Open" value={fmtINR(quote?.open ?? null)} />
        <Stat label="Prev Close" value={fmtINR(quote?.prev_close ?? null)} />
        <Stat label="Day High" value={fmtINR(quote?.day_high ?? null)} />
        <Stat label="Day Low" value={fmtINR(quote?.day_low ?? null)} />
        <Stat
          label="Volume"
          value={quote?.volume ? quote.volume.toLocaleString() : "—"}
        />
      </div>
      {errorMsg ? <div className="quote-header__error">{errorMsg}</div> : null}
    </header>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="quote-stat">
      <span className="quote-stat__label">{label}</span>
      <span className="quote-stat__value">{value}</span>
    </div>
  );
}
