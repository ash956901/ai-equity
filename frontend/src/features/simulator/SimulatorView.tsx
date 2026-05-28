import { useCallback, useEffect, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Award,
  Gamepad2,
  IndianRupee,
  Loader2,
  Search,
  Star,
  TrendingDown,
  TrendingUp,
  Trophy,
  Zap,
} from "lucide-react";

import { PageHeader } from "../../shared/ui/PageHeader";
import { searchCompaniesDB } from "../../lib/api";
import type { AICompany } from "../../lib/api";

type DataMode = "live" | "demo";

interface OpenPosition {
  trade_id: string;
  company_id: string;
  company_name: string;
  ticker: string;
  quantity: number;
  entry_price: number;
  current_price: number | null;
  total_invested: number;
  unrealised_pnl: number | null;
  return_pct: number | null;
  opened_at: string;
}

interface ClosedTrade {
  trade_id: string;
  company_name: string;
  ticker: string;
  trade_type: string;
  quantity: number;
  entry_price: number;
  total_value: number;
  pnl: number | null;
  opened_at: string;
  closed_at: string | null;
}

interface Badge {
  id: string;
  name: string;
  earned: boolean;
}

interface LevelInfo {
  level: number;
  level_name: string;
  xp: number;
  next_level_xp: number | null;
  progress_pct: number;
}

interface SimStats {
  balance: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  win_rate_pct: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
  xp: number;
  level: LevelInfo;
  badges: Badge[];
  current_streak: number;
  best_streak: number;
  daily_challenge: { id: string; text: string; sector: string; done: boolean };
}

interface SimulatorViewProps {
  dataMode: DataMode;
  pushToast: (message: string, tone?: "info" | "success" | "warning") => void;
}

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
}

const BACKEND = import.meta.env.VITE_AI_BACKEND_URL || "http://localhost:8001";

async function apiFetch<T>(path: string): Promise<T> {
  const r = await fetch(`${BACKEND}${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BACKEND}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Request failed");
  }
  return r.json() as Promise<T>;
}

function pnlColor(val: number | null): string {
  if (val === null) return "var(--text-muted)";
  return val >= 0 ? "var(--color-positive, #22c55e)" : "var(--color-negative, #ef4444)";
}

function fmt(n: number | null, prefix = "₹"): string {
  if (n === null) return "—";
  return `${prefix}${Math.abs(n).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export function SimulatorView({ dataMode, pushToast }: SimulatorViewProps) {
  const userId = getUserId();

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<AICompany[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState<AICompany | null>(null);
  const [companyId, setCompanyId] = useState<string | null>(null);
  const [tradeType, setTradeType] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState(1);
  const [tradeLoading, setTradeLoading] = useState(false);

  const [positions, setPositions] = useState<OpenPosition[]>([]);
  const [history, setHistory] = useState<ClosedTrade[]>([]);
  const [stats, setStats] = useState<SimStats | null>(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"positions" | "history">("positions");

  const loadData = useCallback(async () => {
    setDataLoading(true);
    try {
      const [posData, histData, statsData] = await Promise.all([
        apiFetch<{ positions: OpenPosition[] }>(`/simulator/positions?user_id=${userId}`),
        apiFetch<{ trades: ClosedTrade[] }>(`/simulator/history?user_id=${userId}`),
        apiFetch<SimStats>(`/simulator/stats?user_id=${userId}`),
      ]);
      setPositions(posData.positions);
      setHistory(histData.trades);
      setStats(statsData);
    } catch {
      // silently continue; stats will remain null
    } finally {
      setDataLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const results = await searchCompaniesDB(searchQuery.trim(), 6);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 400);
    return () => clearTimeout(t);
  }, [searchQuery]);

  const handleSelectCompany = useCallback((company: AICompany) => {
    setSelectedCompany(company);
    setSearchQuery(company.name);
    setSearchResults([]);
    setCompanyId(company.id);
  }, []);

  const handleTrade = useCallback(async () => {
    if (!companyId || !selectedCompany) {
      pushToast("Select a company first.", "warning");
      return;
    }
    if (quantity < 1) {
      pushToast("Quantity must be at least 1.", "warning");
      return;
    }
    setTradeLoading(true);
    try {
      const result = await apiPost<{
        trade_type: string;
        company_name: string;
        price: number;
        total_value: number;
        pnl?: number;
        balance_after: number;
        xp_earned: number;
        badges_earned: string[];
      }>("/simulator/trade", {
        user_id: userId,
        company_id: companyId,
        trade_type: tradeType,
        quantity,
      });

      const verb = result.trade_type === "buy" ? "Bought" : "Sold";
      const pnlStr = result.pnl !== undefined ? ` | P&L: ₹${result.pnl >= 0 ? "+" : ""}${result.pnl.toFixed(2)}` : "";
      pushToast(
        `${verb} ${quantity}x ${result.company_name} @ ₹${result.price.toFixed(2)}${pnlStr} | +${result.xp_earned} XP`,
        "success"
      );

      if (result.badges_earned.length > 0) {
        setTimeout(() => {
          pushToast(`Badge earned: ${result.badges_earned.join(", ")}!`, "success");
        }, 800);
      }

      await loadData();
      setQuantity(1);
    } catch (err) {
      pushToast(err instanceof Error ? err.message : "Trade failed.", "warning");
    } finally {
      setTradeLoading(false);
    }
  }, [companyId, selectedCompany, quantity, tradeType, userId, pushToast, loadData]);

  const level = stats?.level;

  return (
    <section className="page-wrap">
      <PageHeader
        title="Paper Trading Simulator"
        subtitle="Trade with virtual ₹10,00,000 at live prices. Earn XP, badges, and beat the market."
        dataMode={dataMode}
        right={
          stats && (
            <div className="sim-balance-badge">
              <IndianRupee size={14} />
              <span>
                {(stats.balance / 100000).toFixed(2)}L available
              </span>
            </div>
          )
        }
      />

      <div className="sim-layout">
        {/* Left: Trade panel */}
        <div className="sim-left">
          {/* Order Panel */}
          <div className="card sim-order-panel">
            <div className="card-header">
              <Gamepad2 size={16} />
              <span>Place Order</span>
              <span className="sim-disclaimer">Simulated — Not Real Money</span>
            </div>

            {/* Company search */}
            <div style={{ position: "relative", marginBottom: 12 }}>
              <div className="search-pill">
                <Search size={13} />
                <input
                  placeholder="Search company (e.g. RELIANCE, TCS)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchLoading && <Loader2 size={13} className="spin" />}
              </div>
              {searchResults.length > 0 && (
                <div className="sim-search-dropdown">
                  {searchResults.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      className="sim-search-result"
                      onClick={() => handleSelectCompany(r)}
                    >
                      <strong>{r.ticker_nse || r.ticker_bse}</strong>
                      <span>{r.name}</span>
                      <span className="sim-exchange-tag">{r.ticker_nse ? "NSE" : "BSE"}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Trade type */}
            <div className="sim-trade-type-row">
              <button
                type="button"
                className={`sim-trade-btn ${tradeType === "buy" ? "sim-trade-btn--buy active" : ""}`}
                onClick={() => setTradeType("buy")}
              >
                <ArrowUp size={14} /> Buy
              </button>
              <button
                type="button"
                className={`sim-trade-btn ${tradeType === "sell" ? "sim-trade-btn--sell active" : ""}`}
                onClick={() => setTradeType("sell")}
              >
                <ArrowDown size={14} /> Sell
              </button>
            </div>

            {/* Quantity */}
            <div className="sim-qty-row">
              <label className="field-label">Quantity</label>
              <div className="sim-qty-input-wrap">
                <button type="button" className="sim-qty-btn" onClick={() => setQuantity((q) => Math.max(1, q - 1))}>
                  −
                </button>
                <input
                  type="number"
                  min={1}
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
                  className="sim-qty-input"
                />
                <button type="button" className="sim-qty-btn" onClick={() => setQuantity((q) => q + 1)}>
                  +
                </button>
              </div>
            </div>

            <button
              type="button"
              className={`primary-btn sim-confirm-btn ${tradeType === "sell" ? "sim-confirm-btn--sell" : ""}`}
              onClick={handleTrade}
              disabled={tradeLoading || !companyId || !selectedCompany}
            >
              {tradeLoading ? (
                <Loader2 size={14} className="spin" />
              ) : (
                <>
                  {tradeType === "buy" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
                  Confirm {tradeType.charAt(0).toUpperCase() + tradeType.slice(1)}
                </>
              )}
            </button>

            {stats && (
              <p className="sim-balance-hint">
                Available: <strong>₹{stats.balance.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</strong>
              </p>
            )}
          </div>

          {/* Stats summary */}
          {stats && (
            <div className="card sim-stats-card">
              <div className="card-header">
                <Trophy size={16} />
                <span>P&L Summary</span>
              </div>
              <div className="sim-stats-grid">
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Total P&L</span>
                  <span className="sim-stat-value" style={{ color: pnlColor(stats.total_pnl) }}>
                    {stats.total_pnl >= 0 ? "+" : ""}₹{Math.abs(stats.total_pnl).toFixed(2)}
                  </span>
                </div>
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Win Rate</span>
                  <span className="sim-stat-value">{stats.win_rate_pct}%</span>
                </div>
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Best Trade</span>
                  <span className="sim-stat-value" style={{ color: "var(--color-positive, #22c55e)" }}>
                    +{fmt(stats.best_trade_pnl)}
                  </span>
                </div>
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Worst Trade</span>
                  <span className="sim-stat-value" style={{ color: "var(--color-negative, #ef4444)" }}>
                    -{fmt(Math.abs(stats.worst_trade_pnl))}
                  </span>
                </div>
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Total Trades</span>
                  <span className="sim-stat-value">{stats.total_trades}</span>
                </div>
                <div className="sim-stat-item">
                  <span className="sim-stat-label">Streak</span>
                  <span className="sim-stat-value">{stats.current_streak} days</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Center: Positions / History */}
        <div className="sim-center">
          <div className="sim-tabs">
            <button
              type="button"
              className={`sim-tab ${activeTab === "positions" ? "active" : ""}`}
              onClick={() => setActiveTab("positions")}
            >
              Open Positions ({positions.length})
            </button>
            <button
              type="button"
              className={`sim-tab ${activeTab === "history" ? "active" : ""}`}
              onClick={() => setActiveTab("history")}
            >
              Trade History ({history.length})
            </button>
          </div>

          {dataLoading ? (
            <div className="sim-loading">
              <Loader2 size={20} className="spin" />
              <span>Loading portfolio…</span>
            </div>
          ) : activeTab === "positions" ? (
            positions.length === 0 ? (
              <div className="sim-empty">
                <Gamepad2 size={32} style={{ color: "var(--text-muted)" }} />
                <p>No open positions yet. Buy your first stock!</p>
              </div>
            ) : (
              <div className="sim-table-wrap">
                <table className="sim-table">
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Qty</th>
                      <th>Entry</th>
                      <th>Current</th>
                      <th>Invested</th>
                      <th>Unrealised P&L</th>
                      <th>Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr key={p.trade_id}>
                        <td>
                          <div className="sim-company-cell">
                            <strong>{p.company_name}</strong>
                            <span className="sim-ticker-tag">{p.ticker}</span>
                          </div>
                        </td>
                        <td>{p.quantity}</td>
                        <td>₹{p.entry_price.toFixed(2)}</td>
                        <td>{p.current_price ? `₹${p.current_price.toFixed(2)}` : "—"}</td>
                        <td>₹{p.total_invested.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                        <td style={{ color: pnlColor(p.unrealised_pnl), fontWeight: 600 }}>
                          {p.unrealised_pnl !== null
                            ? `${p.unrealised_pnl >= 0 ? "+" : ""}₹${Math.abs(p.unrealised_pnl).toFixed(2)}`
                            : "—"}
                        </td>
                        <td style={{ color: pnlColor(p.return_pct) }}>
                          {p.return_pct !== null ? `${p.return_pct >= 0 ? "+" : ""}${p.return_pct.toFixed(2)}%` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : history.length === 0 ? (
            <div className="sim-empty">
              <TrendingUp size={32} style={{ color: "var(--text-muted)" }} />
              <p>No closed trades yet.</p>
            </div>
          ) : (
            <div className="sim-table-wrap">
              <table className="sim-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Type</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Value</th>
                    <th>Realised P&L</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((t) => (
                    <tr key={t.trade_id}>
                      <td>
                        <div className="sim-company-cell">
                          <strong>{t.company_name}</strong>
                          <span className="sim-ticker-tag">{t.ticker}</span>
                        </div>
                      </td>
                      <td>
                        <span className={`sim-type-badge sim-type-badge--${t.trade_type}`}>
                          {t.trade_type.toUpperCase()}
                        </span>
                      </td>
                      <td>{t.quantity}</td>
                      <td>₹{t.entry_price.toFixed(2)}</td>
                      <td>₹{t.total_value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}</td>
                      <td style={{ color: pnlColor(t.pnl), fontWeight: 600 }}>
                        {t.pnl !== null ? `${t.pnl >= 0 ? "+" : ""}₹${Math.abs(t.pnl).toFixed(2)}` : "—"}
                      </td>
                      <td>{t.closed_at ? new Date(t.closed_at).toLocaleDateString("en-IN") : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Gamification */}
        {stats && (
          <div className="sim-right">
            {/* XP Level */}
            <div className="card sim-xp-card">
              <div className="card-header">
                <Zap size={16} />
                <span>Level {level?.level}: {level?.level_name}</span>
              </div>
              <div className="sim-xp-bar-wrap">
                <div className="sim-xp-bar">
                  <div
                    className="sim-xp-bar-fill"
                    style={{ width: `${level?.progress_pct ?? 0}%` }}
                  />
                </div>
                <span className="sim-xp-label">
                  {level?.xp} XP {level?.next_level_xp ? `/ ${level.next_level_xp}` : "(Max)"}
                </span>
              </div>
            </div>

            {/* Daily Challenge */}
            {stats.daily_challenge && (
              <div className={`card sim-challenge-card ${stats.daily_challenge.done ? "sim-challenge-card--done" : ""}`}>
                <div className="card-header">
                  <Star size={16} />
                  <span>Daily Challenge</span>
                  {stats.daily_challenge.done && (
                    <span className="sim-done-badge">Done!</span>
                  )}
                </div>
                <p className="sim-challenge-text">{stats.daily_challenge.text}</p>
                {!stats.daily_challenge.done && (
                  <p className="sim-challenge-reward">+25 XP on completion</p>
                )}
              </div>
            )}

            {/* Badges */}
            <div className="card sim-badges-card">
              <div className="card-header">
                <Award size={16} />
                <span>Badges</span>
              </div>
              <div className="sim-badges-grid">
                {stats.badges.map((b) => (
                  <div
                    key={b.id}
                    className={`sim-badge ${b.earned ? "sim-badge--earned" : "sim-badge--locked"}`}
                    title={b.name}
                  >
                    <Trophy size={18} />
                    <span>{b.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Win Rate mini chart */}
            <div className="card sim-winrate-card">
              <div className="card-header">
                <TrendingUp size={16} />
                <span>Performance</span>
              </div>
              <div className="sim-winrate-row">
                <div className="sim-winrate-bar-bg">
                  <div
                    className="sim-winrate-bar-fill"
                    style={{ width: `${stats.win_rate_pct}%` }}
                  />
                </div>
                <span className="sim-winrate-label">{stats.win_rate_pct}% win rate</span>
              </div>
              <div className="sim-perf-row">
                <TrendingUp size={12} style={{ color: "var(--color-positive, #22c55e)" }} />
                <span>Best: {fmt(stats.best_trade_pnl)}</span>
                <TrendingDown size={12} style={{ color: "var(--color-negative, #ef4444)" }} />
                <span>Worst: {fmt(stats.worst_trade_pnl)}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
