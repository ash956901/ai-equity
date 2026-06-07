import { useCallback, useEffect, useState } from "react";
import { GitBranch, Loader2, RefreshCw, Sparkles, ChevronDown, ChevronUp } from "lucide-react";

import {
  fetchCausalMarket,
  fetchCausalPortfolioCompanies,
  fetchCausalCompany,
  analyzeCausalTrigger,
  type CausalMarketData,
  type CausalCompanyData,
  type CausalExposure,
  type CausalChainItem,
  type CausalLLMData,
  type CausalLLMImpact,
} from "../../lib/api";
import { PageHeader } from "../../shared/ui/PageHeader";
import { CompanySearchInput } from "../../shared/components/CompanySearchInput";

type DataMode = "live" | "demo";
type ToastTone = "info" | "success" | "warning";
type Mode = "portfolio" | "company" | "market";
type SeverityFilter = "all" | "serious" | "moderate" | "neutral";
type Severity = "serious" | "moderate" | "neutral";

interface DominoEffectViewProps {
  dataMode: DataMode;
  pushToast: (message: string, tone?: ToastTone) => void;
}

// ── Severity classification ──────────────────────────────────────────────────

function portfolioSeverity(p: CausalPortfolioPattern): Severity {
  const abs = Math.abs(p.price_change_pct);
  if (abs >= 5 && p.confidence >= 0.7) return "serious";
  if (abs >= 2 || p.confidence >= 0.5) return "moderate";
  return "neutral";
}

function exposureSeverity(e: CausalExposure): Severity {
  if (e.impact_magnitude === "high" && Math.abs(e.current_change_pct) >= 2) return "serious";
  if (e.impact_magnitude === "medium" || Math.abs(e.current_change_pct) >= 1) return "moderate";
  return "neutral";
}

function chainSeverity(c: CausalChainItem): Severity {
  if (c.confidence >= 0.75 && Math.abs(c.current_commodity_change_pct) >= 3) return "serious";
  if (c.confidence >= 0.5 || Math.abs(c.current_commodity_change_pct) >= 1) return "moderate";
  return "neutral";
}

function llmSeverity(i: CausalLLMImpact): Severity {
  if (i.confidence >= 0.75) return "serious";
  if (i.confidence >= 0.5) return "moderate";
  return "neutral";
}

// ── Hop chain helpers ────────────────────────────────────────────────────────

function commodityIcon(symbol: string): string {
  const s = symbol.toUpperCase();
  if (s.includes("WTI") || s.includes("BRENT") || s.includes("OIL") || s.includes("DIESEL") || s.includes("JET")) return "🛢";
  if (s.includes("GAS")) return "⚡";
  if (s.includes("XAU") || s.includes("GOLD")) return "🏅";
  if (s.includes("COAL")) return "⛏";
  if (s.includes("SUGAR") || s.includes("WHEAT") || s.includes("CORN") || s.includes("COFFEE")) return "🌾";
  if (s.includes("COPPER") || s.includes("ALUM") || s.includes("XAG")) return "🔩";
  if (s.includes("USD") || s.includes("INR")) return "💱";
  return "📦";
}

function hopIcon(hop: string, index: number): string {
  if (index === 0) return "🌐";
  if (hop.includes("_USD") || hop.includes("_INR") || hop.includes("CRUDE") || hop.includes("FUEL") || hop.includes("GAS") || hop.includes("COAL") || hop.includes("XAU") || hop.includes("sugar") || hop.includes("copper")) return commodityIcon(hop);
  if (index >= 2) return "🏭";
  return "📦";
}

function HopChain({ hops }: { hops: string[] }) {
  const filtered = hops.filter(Boolean);
  return (
    <div className="domino-hop-chain">
      {filtered.map((hop, i) => (
        <span key={`${hop}-${i}`} style={{ display: "contents" }}>
          <span className="domino-hop">
            {hopIcon(hop, i)} {hop.replace(/_/g, " ")}
          </span>
          {i < filtered.length - 1 && <span className="domino-arrow">→</span>}
        </span>
      ))}
    </div>
  );
}

// ── Severity badge ───────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: Severity }) {
  const labels: Record<Severity, string> = {
    serious: "🔴 Serious",
    moderate: "🟡 Moderate",
    neutral: "⚪ No Effect",
  };
  return <span className={`domino-severity-badge ${severity}`}>{labels[severity]}</span>;
}

// ── Individual impact card ───────────────────────────────────────────────────

interface DominoCardProps {
  severity: Severity;
  title: string;
  hops: string[];
  reasoning: string;
  confidence?: number;
  direction?: string;
  tags?: string[];
}

function DominoCard({ severity, title, hops, reasoning, confidence, direction, tags }: DominoCardProps) {
  return (
    <div className={`domino-card ${severity}`}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
        <SeverityBadge severity={severity} />
        <span style={{ fontSize: "0.88rem", fontWeight: 600, color: "var(--ink)", flex: 1 }}>{title}</span>
      </div>
      <HopChain hops={hops} />
      <p className="domino-reasoning">{reasoning}</p>
      <div className="domino-meta-row">
        {confidence != null && (
          <span className="chip">Confidence: {(confidence * 100).toFixed(0)}%</span>
        )}
        {direction && (
          <span className={`chip ${direction === "positive" ? "positive" : direction === "negative" ? "negative" : ""}`}>
            {direction}
          </span>
        )}
        {tags?.map((tag) => (
          <span key={tag} className="chip" style={{ background: "color-mix(in srgb, var(--brand) 10%, transparent)", color: "var(--brand)", borderColor: "color-mix(in srgb, var(--brand) 25%, transparent)" }}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Grouped card list with neutral collapse ──────────────────────────────────

interface CardGroup {
  severity: Severity;
  title: string;
  hops: string[];
  reasoning: string;
  confidence?: number;
  direction?: string;
  tags?: string[];
}

function CardList({ cards, filter }: { cards: CardGroup[]; filter: SeverityFilter }) {
  const [showNeutral, setShowNeutral] = useState(false);

  const visible = filter === "all" ? cards : cards.filter((c) => c.severity === filter);
  const serious = visible.filter((c) => c.severity === "serious");
  const moderate = visible.filter((c) => c.severity === "moderate");
  const neutral = visible.filter((c) => c.severity === "neutral");

  if (visible.length === 0) {
    return <div className="notice">No signals match the selected filter.</div>;
  }

  return (
    <>
      {serious.map((c, i) => <DominoCard key={`s-${i}`} {...c} />)}
      {moderate.map((c, i) => <DominoCard key={`m-${i}`} {...c} />)}
      {filter === "all" && neutral.length > 0 && (
        <>
          <button type="button" className="domino-neutral-toggle" onClick={() => setShowNeutral(!showNeutral)}>
            {showNeutral ? <ChevronUp size={13} style={{ display: "inline", marginRight: 4 }} /> : <ChevronDown size={13} style={{ display: "inline", marginRight: 4 }} />}
            {showNeutral ? "Hide" : `Show ${neutral.length} no-effect signal${neutral.length !== 1 ? "s" : ""}`}
          </button>
          {showNeutral && neutral.map((c, i) => <DominoCard key={`n-${i}`} {...c} />)}
        </>
      )}
      {filter === "neutral" && neutral.map((c, i) => <DominoCard key={`n-${i}`} {...c} />)}
    </>
  );
}

// ── Main view ────────────────────────────────────────────────────────────────

export function DominoEffectView({ dataMode, pushToast }: DominoEffectViewProps) {
  const [mode, setMode] = useState<Mode>("portfolio");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [marketData, setMarketData] = useState<CausalMarketData | null>(null);
  const [portfolioCompanies, setPortfolioCompanies] = useState<CausalCompanyData[]>([]);
  const [portfolioRefreshedAt, setPortfolioRefreshedAt] = useState<string | null>(null);
  const [companyData, setCompanyData] = useState<CausalCompanyData | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<{ id: string; name: string } | null>(null);
  const [llmData, setLlmData] = useState<CausalLLMData | null>(null);
  const [llmLoading, setLlmLoading] = useState(false);
  const [showGeoEvents, setShowGeoEvents] = useState(false);
  const [showNewsImpacts, setShowNewsImpacts] = useState(false);

  const userId = localStorage.getItem("equityai-user-id") ?? "00000000-0000-0000-0000-000000000001";

  const loadPortfolio = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCausalPortfolioCompanies(userId);
      setPortfolioCompanies(data.companies ?? []);
      setPortfolioRefreshedAt(data.last_refreshed_at ?? null);
    } catch {
      setError("Could not load portfolio causal data.");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  const loadMarket = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCausalMarket();
      setMarketData(data);
    } catch {
      setError("Could not load market causal data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mode === "portfolio") void loadPortfolio();
    else if (mode === "market") void loadMarket();
  }, [mode, loadPortfolio, loadMarket]);

  async function handleCompanySelect(company: { id: string; name: string; ticker: string }) {
    setSelectedCompany({ id: company.id, name: company.name });
    setCompanyData(null);
    setLlmData(null);
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCausalCompany(company.id);
      setCompanyData(data);
    } catch {
      setError(`Could not load causal data for ${company.name}.`);
    } finally {
      setLoading(false);
    }
  }

  async function handleLLMAnalyze() {
    if (!selectedCompany) return;
    setLlmLoading(true);
    try {
      const trigger =
        `Hidden causal impacts for ${selectedCompany.name}: ` +
        `top customers, supply chain dependencies, and 2nd-order sector risks`;
      const data = await analyzeCausalTrigger(trigger, selectedCompany.id);
      setLlmData(data);
      pushToast("Deep AI analysis complete", "success");
    } catch {
      pushToast("AI analysis failed — try again", "warning");
    } finally {
      setLlmLoading(false);
    }
  }

  // ── Portfolio cards — one group per holding company ───────────────────────
  const portfolioCardGroups: Array<{ company: CausalCompanyData; cards: CardGroup[] }> =
    portfolioCompanies.map((company) => ({
      company,
      cards: company.exposures.map((e) => ({
        severity: exposureSeverity(e),
        title: `${e.commodity} ${e.commodity_direction === "up" ? "↑" : e.commodity_direction === "down" ? "↓" : "→"} → ${company.company_name} (${e.dependency_type})`,
        hops: [e.commodity, company.sector, company.company_name],
        reasoning: `${e.commodity} is a ${e.dependency_type} dependency for the ${company.sector} sector (${e.impact_magnitude} magnitude). Current move: ${e.current_change_pct >= 0 ? "+" : ""}${e.current_change_pct.toFixed(1)}%. Impact direction: ${e.impact_direction}.${e.affected_companies.length ? ` Affected peers: ${e.affected_companies.slice(0, 3).join(", ")}.` : ""}`,
        direction: e.impact_direction,
        tags: [e.commodity, e.impact_magnitude],
      })),
    }));

  const totalPortfolioExposures = portfolioCardGroups.reduce((sum, g) => sum + g.cards.length, 0);

  // ── Company exposure cards ───────────────────────────────────────────────
  const exposureCards: CardGroup[] = (companyData?.exposures ?? []).map((e) => ({
    severity: exposureSeverity(e),
    title: `${e.commodity} ${e.commodity_direction === "up" ? "↑" : e.commodity_direction === "down" ? "↓" : "→"} → ${companyData?.company_name} (${e.dependency_type})`,
    hops: [e.commodity, companyData?.sector ?? "", companyData?.company_name ?? ""],
    reasoning: `${e.commodity} is a ${e.dependency_type} dependency for the ${companyData?.sector} sector (${e.impact_magnitude} magnitude). Current move: ${e.current_change_pct >= 0 ? "+" : ""}${e.current_change_pct.toFixed(1)}%. Impact direction: ${e.impact_direction}.${e.affected_companies.length ? ` Affected peers: ${e.affected_companies.slice(0, 3).join(", ")}.` : ""}`,
    confidence: undefined,
    direction: e.impact_direction,
    tags: [e.commodity, e.impact_magnitude],
  }));

  const llmCards: CardGroup[] = [
    ...(llmData?.primary_impacts ?? []).map((i) => ({
      severity: llmSeverity(i),
      title: `[Primary] ${i.sector} — ${i.direction}`,
      hops: [llmData?.trigger_type ?? "Trigger", i.sector],
      reasoning: i.reasoning,
      confidence: i.confidence,
      direction: i.direction,
      tags: ["AI · Primary"],
    })),
    ...(llmData?.hidden_impacts ?? []).map((i) => ({
      severity: llmSeverity(i),
      title: `[Hidden] ${i.sector} — ${i.direction}`,
      hops: [llmData?.trigger_type ?? "Trigger", "Hidden Chain", i.sector],
      reasoning: i.reasoning,
      confidence: i.confidence,
      direction: i.direction,
      tags: ["AI · Hidden"],
    })),
  ];

  // ── Market chain cards ───────────────────────────────────────────────────
  const marketCards: CardGroup[] = (marketData?.causal_chains ?? []).map((c) => ({
    severity: chainSeverity(c),
    title: c.name,
    hops: [c.trigger_value, c.hop1_target, c.hop2_target, c.hop3_target].filter(Boolean) as string[],
    reasoning: `${c.trigger_value} → ${c.hop1_target} (${c.hop1_relationship?.replace(/_/g, " ")})${c.hop2_target ? ` → ${c.hop2_target} (${c.hop2_relationship?.replace(/_/g, " ")})` : ""}${c.hop3_target ? ` → ${c.hop3_target} (${c.hop3_relationship?.replace(/_/g, " ")})` : ""}. Current commodity move: ${c.current_commodity_change_pct >= 0 ? "+" : ""}${c.current_commodity_change_pct.toFixed(1)}%.`,
    confidence: c.confidence,
    tags: [c.trigger_type.replace(/_/g, " ")],
  }));

  const SEVERITY_FILTERS: { key: SeverityFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "serious", label: "🔴 Serious" },
    { key: "moderate", label: "🟡 Moderate" },
    { key: "neutral", label: "⚪ No Effect" },
  ];

  return (
    <section className="page-wrap">
      <PageHeader
        title="Domino Effect"
        subtitle="Hidden causal chains: world events → commodities → sectors → your holdings."
        dataMode={dataMode}
        right={
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => {
              if (mode === "portfolio") void loadPortfolio();
              else if (mode === "market") void loadMarket();
            }}
            disabled={loading}
          >
            <RefreshCw size={13} style={{ display: "inline", marginRight: 4 }} />
            Refresh
          </button>
        }
      />

      {/* Data freshness indicator */}
      {(portfolioRefreshedAt || marketData?.last_refreshed_at) && (
        <div style={{ fontSize: "11px", color: "var(--text-muted)", padding: "0 16px 4px", opacity: 0.7 }}>
          Data as of {new Date(
            (portfolioRefreshedAt || marketData?.last_refreshed_at) as string
          ).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" })} IST
        </div>
      )}

      {/* Mode tabs */}
      <div className="domino-tabs">
        {(["portfolio", "company", "market"] as Mode[]).map((m) => (
          <button
            key={m}
            type="button"
            className={`domino-tab ${mode === m ? "active" : ""}`}
            onClick={() => { setMode(m); setSeverityFilter("all"); }}
          >
            {m === "portfolio" ? "My Portfolio" : m === "company" ? "Company Search" : "Market-Wide"}
          </button>
        ))}
      </div>

      {/* Severity filter bar */}
      <div className="domino-filter-row">
        {SEVERITY_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`domino-filter-btn ${severityFilter === f.key ? "active" : ""}`}
            onClick={() => setSeverityFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="notice warning">{error}</div>}

      {loading && (
        <div className="notice" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Loader2 size={14} className="spin" />
          Analysing causal chains…
        </div>
      )}

      {/* ── PORTFOLIO TAB ── */}
      {mode === "portfolio" && !loading && !error && (
        <>
          {portfolioCardGroups.length === 0 ? (
            <div className="notice">
              <GitBranch size={14} style={{ display: "inline", marginRight: 6 }} />
              No holdings found. Add companies to your portfolio to see causal exposures.
            </div>
          ) : (
            <>
              <div className="notice" style={{ marginBottom: 12 }}>
                {portfolioCardGroups.length} holding{portfolioCardGroups.length !== 1 ? "s" : ""} · {totalPortfolioExposures} total commodity exposure{totalPortfolioExposures !== 1 ? "s" : ""}
              </div>
              {portfolioCardGroups.map(({ company, cards }) => (
                <div key={company.company_id} style={{ marginBottom: 20 }}>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--brand)", padding: "4px 0 8px", borderBottom: "1px solid var(--border)", marginBottom: 8 }}>
                    {company.company_name}
                    {company.ticker && <span style={{ fontWeight: 400, color: "var(--muted)", marginLeft: 6 }}>({company.ticker})</span>}
                    <span style={{ fontWeight: 400, color: "var(--muted)", marginLeft: 8 }}>{company.sector}</span>
                  </div>
                  {cards.length === 0 ? (
                    <div className="notice" style={{ fontSize: "0.8rem" }}>
                      No commodity exposures tracked for {company.sector} sector yet.
                    </div>
                  ) : (
                    <CardList cards={cards} filter={severityFilter} />
                  )}
                </div>
              ))}
            </>
          )}
        </>
      )}

      {/* ── COMPANY TAB ── */}
      {mode === "company" && (
        <>
          <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
            <CompanySearchInput
              placeholder="Search a company to analyse causal exposure…"
              onSelect={(c) => void handleCompanySelect(c)}
              className="w-80"
            />
            {selectedCompany && (
              <button
                type="button"
                className="primary-btn"
                onClick={() => void handleLLMAnalyze()}
                disabled={llmLoading}
                style={{ display: "flex", alignItems: "center", gap: 6 }}
              >
                {llmLoading
                  ? <><Loader2 size={13} className="spin" /> Analysing…</>
                  : <><Sparkles size={13} /> Run Deep AI Analysis</>}
              </button>
            )}
          </div>

          {!loading && companyData && (
            <>
              <div className="notice" style={{ marginBottom: 12 }}>
                <strong>{companyData.company_name}</strong> — {companyData.sector} — {companyData.exposures.length} commodity exposure{companyData.exposures.length !== 1 ? "s" : ""} found
              </div>
              <CardList cards={[...exposureCards, ...llmCards]} filter={severityFilter} />

              {/* LLM opportunities, risks & recommendations summary */}
              {llmData && (
                <div style={{ marginTop: 16 }}>
                  {(llmData.opportunities?.length ?? 0) > 0 && (
                    <div className="feature-card" style={{ marginBottom: 12 }}>
                      <div className="feature-head">
                        <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--good)" }}>Opportunities</span>
                      </div>
                      <div className="chip-row" style={{ marginTop: 8 }}>
                        {llmData.opportunities.map((o, i) => (
                          <span key={i} className="chip positive">{o}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {(llmData.risks?.length ?? 0) > 0 && (
                    <div className="feature-card" style={{ marginBottom: 12 }}>
                      <div className="feature-head">
                        <span style={{ fontSize: "0.82rem", fontWeight: 700, color: "var(--bad)" }}>Risks</span>
                      </div>
                      <div className="chip-row" style={{ marginTop: 8 }}>
                        {llmData.risks.map((r, i) => (
                          <span key={i} className="chip negative">{r}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {llmData.recommendations && (
                    (llmData.recommendations.monitor?.length ?? 0) > 0 ||
                    (llmData.recommendations.mitigate?.length ?? 0) > 0 ||
                    (llmData.recommendations.entry_points?.length ?? 0) > 0
                  ) && (
                    <div className="feature-card" style={{ marginBottom: 12 }}>
                      <div className="feature-head">
                        <span style={{ fontSize: "0.82rem", fontWeight: 700 }}>AI Recommendations</span>
                      </div>
                      <div style={{ marginTop: 8, fontSize: "0.83rem" }}>
                        {(llmData.recommendations.monitor?.length ?? 0) > 0 && (
                          <div style={{ marginBottom: 6 }}>
                            <strong>Monitor:</strong>
                            <div className="chip-row" style={{ marginTop: 4 }}>
                              {llmData.recommendations.monitor.map((m, i) => (
                                <span key={i} className="chip">{m}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {(llmData.recommendations.mitigate?.length ?? 0) > 0 && (
                          <div style={{ marginBottom: 6 }}>
                            <strong>Mitigate:</strong>
                            <div className="chip-row" style={{ marginTop: 4 }}>
                              {llmData.recommendations.mitigate.map((m, i) => (
                                <span key={i} className="chip negative">{m}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {(llmData.recommendations.entry_points?.length ?? 0) > 0 && (
                          <div>
                            <strong>Entry points:</strong>
                            <div className="chip-row" style={{ marginTop: 4 }}>
                              {llmData.recommendations.entry_points.map((e, i) => (
                                <span key={i} className="chip positive">{e}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  {(llmData.opportunities?.length ?? 0) === 0 &&
                   (llmData.risks?.length ?? 0) === 0 &&
                   (llmData.recommendations?.monitor?.length ?? 0) === 0 &&
                   (llmData.recommendations?.mitigate?.length ?? 0) === 0 &&
                   (llmData.recommendations?.entry_points?.length ?? 0) === 0 && (
                    <div className="notice">
                      No hidden causal chains identified for this company. This may be because the company has no tracked commodity exposures, or the AI found no significant 2nd-order risk signals.
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {!loading && !companyData && !error && (
            <div className="notice">
              <GitBranch size={14} style={{ display: "inline", marginRight: 6 }} />
              Search a company above to see its commodity and sector causal exposure.
            </div>
          )}
        </>
      )}

      {/* ── MARKET TAB ── */}
      {mode === "market" && !loading && marketData && (
        <>
          <div className="notice" style={{ marginBottom: 12 }}>
            {marketData.causal_chains.length} active causal chain{marketData.causal_chains.length !== 1 ? "s" : ""} tracked · {Object.keys(marketData.commodity_trends).length} commodities monitored
          </div>

          <CardList cards={marketCards} filter={severityFilter} />

          {/* Commodity snapshot */}
          {Object.keys(marketData.commodity_trends).length > 0 && (
            <div className="table-card" style={{ marginTop: 16 }}>
              <div className="table-head"><h3>Commodity Snapshot</h3></div>
              {Object.entries(marketData.commodity_trends)
                .sort((a, b) => Math.abs(b[1].change_pct) - Math.abs(a[1].change_pct))
                .map(([symbol, trend]) => (
                  <div key={symbol} className="table-row" style={{ display: "grid", gridTemplateColumns: "1fr auto auto", gap: 12, alignItems: "center" }}>
                    <span>
                      {commodityIcon(symbol)} {trend.name || symbol}
                      <small style={{ display: "block", fontSize: "0.75rem", color: "var(--muted)" }}>{symbol}</small>
                    </span>
                    <span style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>
                      {trend.current_price != null ? `$${trend.current_price.toLocaleString()}` : "—"}
                    </span>
                    <span className={trend.change_pct >= 0 ? "positive" : "negative"} style={{ fontWeight: 600, fontSize: "0.85rem" }}>
                      {trend.change_pct >= 0 ? "+" : ""}{trend.change_pct.toFixed(1)}%
                    </span>
                  </div>
                ))}
            </div>
          )}

          {/* Geo events collapsible */}
          {marketData.geopolitical_events.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <button type="button" className="domino-neutral-toggle" onClick={() => setShowGeoEvents(!showGeoEvents)}>
                {showGeoEvents ? <ChevronUp size={13} style={{ display: "inline", marginRight: 4 }} /> : <ChevronDown size={13} style={{ display: "inline", marginRight: 4 }} />}
                {showGeoEvents ? "Hide" : `Show ${marketData.geopolitical_events.length} geopolitical event${marketData.geopolitical_events.length !== 1 ? "s" : ""}`}
              </button>
              {showGeoEvents && (
                <div style={{ marginTop: 8 }}>
                  {marketData.geopolitical_events.map((ev, i) => (
                    <div key={i} className="domino-card neutral" style={{ marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                        <p style={{ margin: 0, fontSize: "0.85rem", fontWeight: 600, color: "var(--ink)" }}>🌐 {ev.title}</p>
                        <div className="chip-row" style={{ flexShrink: 0 }}>
                          <span className="chip">{ev.country}</span>
                          {ev.category && <span className="chip">{ev.category}</span>}
                          {ev.confidence != null && <span className="chip">{(ev.confidence * 100).toFixed(0)}% conf</span>}
                        </div>
                      </div>
                      {ev.goldstein_scale != null && (
                        <p style={{ margin: "6px 0 0", fontSize: "0.78rem", color: "var(--muted)" }}>
                          Goldstein scale: {ev.goldstein_scale.toFixed(1)} {ev.goldstein_scale <= -5 ? "⚠️ destabilising" : ev.goldstein_scale >= 5 ? "✅ stabilising" : ""}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* News impacts collapsible */}
          {marketData.news_impacts.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <button type="button" className="domino-neutral-toggle" onClick={() => setShowNewsImpacts(!showNewsImpacts)}>
                {showNewsImpacts ? <ChevronUp size={13} style={{ display: "inline", marginRight: 4 }} /> : <ChevronDown size={13} style={{ display: "inline", marginRight: 4 }} />}
                {showNewsImpacts ? "Hide" : `Show ${marketData.news_impacts.length} news impact${marketData.news_impacts.length !== 1 ? "s" : ""}`}
              </button>
              {showNewsImpacts && (
                <div style={{ marginTop: 8 }}>
                  {marketData.news_impacts.map((n, i) => (
                    <div key={i} className={`domino-card ${n.impact_direction === "negative" ? "serious" : n.impact_direction === "positive" ? "moderate" : "neutral"}`} style={{ marginBottom: 8 }}>
                      <p style={{ margin: 0, fontSize: "0.85rem", fontWeight: 600, color: "var(--ink)" }}>📰 {n.title}</p>
                      <div className="domino-meta-row">
                        {n.source && <span className="chip">{n.source}</span>}
                        {n.commodity && <span className="chip">{n.commodity}</span>}
                        {n.sector && <span className="chip">{n.sector}</span>}
                        {n.impact_direction && (
                          <span className={`chip ${n.impact_direction === "positive" ? "positive" : n.impact_direction === "negative" ? "negative" : ""}`}>
                            {n.impact_direction}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
