import { useEffect, useState } from "react";
import { X, TrendingUp, Newspaper, Bot } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchHistoricalPrices,
  fetchTimeline,
  streamChatQuery,
  type AIHistoricalPrices,
  type TimelineEvent,
} from "../../lib/api";

interface Holding {
  companyId: string;
  symbol: string;
  company: string;
  sector: string;
  returnPct: number;
  weight: number;
}

interface Props {
  holding: Holding;
  onClose: () => void;
}

function sentimentColor(sentiment: string | undefined): string {
  if (!sentiment) return "var(--muted)";
  const s = sentiment.toLowerCase();
  if (s === "positive" || s === "bullish") return "var(--good)";
  if (s === "negative" || s === "bearish") return "var(--bad)";
  return "var(--muted)";
}

export function HoldingDetailPanel({ holding, onClose }: Props) {
  const [prices, setPrices] = useState<AIHistoricalPrices | null>(null);
  const [news, setNews] = useState<TimelineEvent[]>([]);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [recLoading, setRecLoading] = useState(false);

  const expertiseLevel = localStorage.getItem("equityai-expertise") ?? "beginner";

  useEffect(() => {
    fetchHistoricalPrices(holding.companyId, 30).then(setPrices).catch(() => {});
    fetchTimeline(undefined, holding.companyId, 3).then(setNews).catch(() => {});

    const userId = localStorage.getItem("equityai-user-id") ?? "11111111-1111-1111-1111-111111111111";
    setRecLoading(true);
    let acc = "";
    streamChatQuery(
      {
        user_id: userId,
        query: `Should I buy, sell, or hold ${holding.company} (${holding.symbol})? Give me a concise 3-line recommendation with reasons based on current market conditions.`,
        expertise_level: expertiseLevel,
      },
      {
        onToken: (t) => {
          acc += t;
          setRecommendation(acc);
          setRecLoading(false);
        },
        onError: (d) => {
          setRecommendation(`Could not fetch recommendation: ${d}`);
          setRecLoading(false);
        },
      },
    )
      .catch(() => setRecommendation("Could not fetch recommendation. Try again later."))
      .finally(() => setRecLoading(false));
  }, [holding.companyId, holding.company, holding.symbol, expertiseLevel]);

  const chartData = prices?.prices.map((p) => ({
    date: p.date.slice(5),
    close: p.close,
  }));

  const priceChange = prices && prices.prices.length >= 2
    ? prices.prices[prices.prices.length - 1].close - prices.prices[0].close
    : 0;
  const isPositive = priceChange >= 0;

  return (
    <div
      style={{
        position: "fixed",
        right: 0,
        top: 0,
        width: 420,
        height: "100vh",
        background: "var(--bg-layer-0, #0c121a)",
        borderLeft: "1px solid var(--border)",
        boxShadow: "-8px 0 32px rgba(0,0,0,0.5)",
        zIndex: 1000,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 0,
      }}
    >
      {/* Header */}
      <div style={{ padding: "20px 20px 16px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", margin: 0 }}>{holding.sector}</p>
          <h2 style={{ margin: "4px 0 2px", fontSize: "1.3rem" }}>{holding.company}</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontFamily: "monospace", fontSize: 13, color: "var(--brand)" }}>{holding.symbol}</span>
            <span style={{ fontSize: 12, color: holding.returnPct >= 0 ? "var(--good)" : "var(--bad)" }}>
              {holding.returnPct >= 0 ? "+" : ""}{holding.returnPct.toFixed(1)}% return
            </span>
          </div>
        </div>
        <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--muted)", padding: 4 }}>
          <X size={20} />
        </button>
      </div>

      {/* Price Chart */}
      <div style={{ padding: 20, borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <TrendingUp size={16} />
          <h4 style={{ margin: 0, fontSize: "0.875rem" }}>30-Day Price</h4>
          {prices && prices.prices.length > 0 && (
            <span style={{ fontSize: 12, color: isPositive ? "var(--good)" : "var(--bad)", marginLeft: "auto" }}>
              {isPositive ? "+" : ""}{((priceChange / prices.prices[0].close) * 100).toFixed(2)}%
            </span>
          )}
        </div>
        {chartData && chartData.length > 0 ? (
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,132,145,0.15)" />
                <XAxis dataKey="date" tick={{ fill: "#7d8792", fontSize: 9 }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#7d8792", fontSize: 9 }} tickLine={false} width={50} tickFormatter={(v) => `₹${Number(v).toLocaleString()}`} />
                <Tooltip
                  formatter={(v: number) => [`₹${v.toLocaleString()}`, "Close"]}
                  contentStyle={{ background: "rgba(12,18,26,0.92)", border: "1px solid rgba(120,132,145,0.25)", borderRadius: 8, fontSize: 12 }}
                />
                <Line type="monotone" dataKey="close" stroke={isPositive ? "#22c55e" : "#ef4444"} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>No price data available.</p>
        )}
      </div>

      {/* Recent News */}
      <div style={{ padding: 20, borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Newspaper size={16} />
          <h4 style={{ margin: 0, fontSize: "0.875rem" }}>Recent News</h4>
        </div>
        {news.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {news.map((ev) => (
              <div key={ev.id} style={{ padding: "8px 10px", background: "var(--bg-elevated)", borderRadius: 8, borderLeft: `3px solid ${sentimentColor(ev.metadata?.sentiment as string)}` }}>
                <p style={{ margin: 0, fontSize: 12, lineHeight: 1.5 }}>{ev.title}</p>
                <span style={{ fontSize: 10, color: "var(--muted)" }}>{new Date(ev.timestamp).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>No recent news found.</p>
        )}
      </div>

      {/* AI Recommendation */}
      <div style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <Bot size={16} />
          <h4 style={{ margin: 0, fontSize: "0.875rem" }}>AI Recommendation</h4>
        </div>
        {recLoading ? (
          <p style={{ fontSize: 13, color: "var(--muted)" }}>Analysing…</p>
        ) : recommendation ? (
          <p style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>{recommendation}</p>
        ) : null}
      </div>
    </div>
  );
}
