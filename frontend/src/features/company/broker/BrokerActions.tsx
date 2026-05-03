import { ExternalLink } from "lucide-react";

interface BrokerActionsProps {
  ticker: string;
  exchange?: string;
}

export function BrokerActions({ ticker, exchange = "NSE" }: BrokerActionsProps) {
  const symbol = `${exchange.toUpperCase()}:${ticker.toUpperCase()}`;
  const kiteUrl = `https://kite.zerodha.com/?stock=${encodeURIComponent(symbol)}`;
  const growwUrl = `https://groww.in/stocks/${ticker.toLowerCase()}`;
  return (
    <div className="broker-actions">
      <a className="broker-actions__btn broker-actions__btn--buy" href={kiteUrl} target="_blank" rel="noreferrer">
        Buy / Sell on Zerodha <ExternalLink size={14} />
      </a>
      <a className="broker-actions__btn" href={growwUrl} target="_blank" rel="noreferrer">
        View on Groww <ExternalLink size={14} />
      </a>
    </div>
  );
}
