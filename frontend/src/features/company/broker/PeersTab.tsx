import { useEffect, useState } from "react";
import { fetchPeers, type PeerCompany } from "../../../shared/api/quotes";

interface PeersTabProps {
  ticker: string;
  onSelect?: (peer: PeerCompany) => void;
}

export function PeersTab({ ticker, onSelect }: PeersTabProps) {
  const [peers, setPeers] = useState<PeerCompany[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchPeers(ticker, 12)
      .then((rows) => {
        if (!cancelled) setPeers(rows);
      })
      .catch(() => {
        if (!cancelled) setPeers([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  if (loading) return <p className="muted">Loading peers…</p>;
  if (!peers.length) return <p className="muted">No peers found.</p>;

  return (
    <table className="peers-table">
      <thead>
        <tr>
          <th>Company</th>
          <th>Industry</th>
          <th>Market cap (Cr)</th>
          <th>P/E</th>
          <th>ROE</th>
        </tr>
      </thead>
      <tbody>
        {peers.map((p) => (
          <tr key={p.company_id} onClick={() => onSelect?.(p)} className="peers-table__row">
            <td>
              <strong>{p.name}</strong>
              <span className="muted"> {p.ticker_nse || p.ticker_bse}</span>
            </td>
            <td>{p.industry || p.sector || "—"}</td>
            <td>{p.market_cap_inr ? p.market_cap_inr.toLocaleString() : "—"}</td>
            <td>{p.pe_ratio ? p.pe_ratio.toFixed(1) : "—"}</td>
            <td>{p.roe ? `${(p.roe * 100).toFixed(1)}%` : "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
