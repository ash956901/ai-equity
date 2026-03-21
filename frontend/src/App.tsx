import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  BarChart3,
  Bot,
  Clock3,
  Compass,
  Command,
  FileText,
  LayoutDashboard,
  Moon,
  Newspaper,
  Search,
  Settings,
  Sparkles,
  Sun,
  TrendingUp,
  Wallet,
} from "lucide-react";
import {
  ApiError,
  fetchApiStatus,
  fetchBackendHealth,
  fetchHoldingsCount,
  fetchMarketHeadlines,
  fetchSecFilings,
  fetchTickerSentiment,
  searchCompanies,
  type ApiStatusResponse,
  type CompanySearchResult,
  type HealthResponse,
  type NewsDataResponse,
  type SecFiling,
  type SentimentFeedResponse,
} from "./lib/api";

type ViewKey =
  | "dashboard"
  | "chat"
  | "discovery"
  | "portfolio"
  | "filings"
  | "timeline"
  | "news"
  | "settings";
type Theme = "light" | "dark";

interface DiscoveryCompany {
  symbol: string;
  name: string;
  sector: string;
  marketCapBn: number;
  insight: string;
  themeScores: Record<string, number>;
}

type MarketCapBucket = "all" | "mega" | "large" | "mid" | "small";

interface TimelineEvent {
  id: string;
  company: string;
  title: string;
  summary: string;
  type: "filing" | "news" | "signal";
  impact: "high" | "medium" | "low";
  timestamp: string;
  sourceLabel: string;
  sourceUrl?: string;
  details: string[];
}

const DISCOVERY_COMPANIES: DiscoveryCompany[] = [
  {
    symbol: "RELIANCE",
    name: "Reliance Industries",
    sector: "Conglomerate",
    marketCapBn: 210,
    insight: "Building strong optionality across AI infra, green energy, and retail data platforms.",
    themeScores: { AI: 82, Renewable: 78, RetailTech: 71, Defense: 48 },
  },
  {
    symbol: "TCS",
    name: "Tata Consultancy Services",
    sector: "IT Services",
    marketCapBn: 170,
    insight: "Enterprise AI transformation mandates remain dominant in large client deals.",
    themeScores: { AI: 90, Cloud: 86, Cybersecurity: 68, Fintech: 59 },
  },
  {
    symbol: "INFY",
    name: "Infosys",
    sector: "IT Services",
    marketCapBn: 78,
    insight: "AI-led digital modernization pipeline indicates sustained large-deal conversion.",
    themeScores: { AI: 88, Cloud: 79, EnterpriseTech: 66, Fintech: 54 },
  },
  {
    symbol: "HAL",
    name: "Hindustan Aeronautics",
    sector: "Aerospace & Defense",
    marketCapBn: 32,
    insight: "Defense electronics and aircraft order visibility continues to improve.",
    themeScores: { Defense: 94, Aerospace: 89, AI: 52, Manufacturing: 74 },
  },
  {
    symbol: "BEL",
    name: "Bharat Electronics",
    sector: "Aerospace & Defense",
    marketCapBn: 18,
    insight: "Mission systems and radar programs support medium-term earnings stability.",
    themeScores: { Defense: 91, Aerospace: 76, AI: 57, Semiconductors: 50 },
  },
  {
    symbol: "TATAPOWER",
    name: "Tata Power",
    sector: "Power & Utilities",
    marketCapBn: 17,
    insight: "Renewable capacity expansion and distribution turnaround are key catalysts.",
    themeScores: { Renewable: 92, EV: 74, GridTech: 63, AI: 49 },
  },
  {
    symbol: "ADANIGREEN",
    name: "Adani Green Energy",
    sector: "Power & Utilities",
    marketCapBn: 31,
    insight: "Scale in utility-scale solar and storage makes it a pure renewable momentum play.",
    themeScores: { Renewable: 95, GridTech: 69, EV: 58, AI: 34 },
  },
  {
    symbol: "M&M",
    name: "Mahindra & Mahindra",
    sector: "Automotive",
    marketCapBn: 39,
    insight: "EV product cadence and farm resilience create a balanced cyclical profile.",
    themeScores: { EV: 86, Manufacturing: 73, RuralDemand: 70, AI: 43 },
  },
  {
    symbol: "ZOMATO",
    name: "Eternal (Zomato)",
    sector: "Internet",
    marketCapBn: 23,
    insight: "Logistics intelligence and retention loops are strengthening operating leverage.",
    themeScores: { RetailTech: 85, AI: 72, Fintech: 67, QuickCommerce: 88 },
  },
  {
    symbol: "PAYTM",
    name: "One97 Communications",
    sector: "Fintech",
    marketCapBn: 4.9,
    insight: "Merchant monetization and compliance-led product redesign remain key watchpoints.",
    themeScores: { Fintech: 90, AI: 63, DigitalPayments: 94, RetailTech: 56 },
  },
];

const TIMELINE_EVENTS: TimelineEvent[] = [
  {
    id: "timeline-1",
    company: "RELIANCE",
    title: "Quarterly operational update published",
    summary: "Retail and digital subscriber momentum remained strong across key reporting lines.",
    type: "filing",
    impact: "high",
    timestamp: "2026-03-21T19:05:00+05:30",
    sourceLabel: "NSE Filing Feed",
    sourceUrl: "#",
    details: [
      "Consumer segment commentary highlighted sustained footfall growth and improving ticket sizes.",
      "Management reiterated capex discipline with selective investments in growth verticals.",
      "Market participants are likely to watch margin trajectory in telecom and retail next quarter.",
    ],
  },
  {
    id: "timeline-2",
    company: "HAL",
    title: "Defense contract pipeline signal strengthened",
    summary: "Follow-on order visibility improved after multiple procurement milestones moved ahead.",
    type: "signal",
    impact: "high",
    timestamp: "2026-03-21T16:50:00+05:30",
    sourceLabel: "Iris Theme Engine",
    details: [
      "Backlog quality remains strong and supports medium-term execution confidence.",
      "Aerospace suppliers linked to HAL may experience positive second-order effects.",
      "Near-term re-rating risk depends on margin preservation and delivery schedules.",
    ],
  },
  {
    id: "timeline-3",
    company: "TCS",
    title: "Large transformation deal referenced in media commentary",
    summary: "AI-focused enterprise transformation mandate signals steady global demand resilience.",
    type: "news",
    impact: "medium",
    timestamp: "2026-03-21T14:20:00+05:30",
    sourceLabel: "Market News Cluster",
    sourceUrl: "#",
    details: [
      "Deal momentum indicates continued demand for cloud modernization and AI integration.",
      "Execution quality and productivity gains may offset pricing pressure concerns.",
      "Peers in IT services could benefit from improved sentiment on discretionary spending.",
    ],
  },
  {
    id: "timeline-4",
    company: "TATAPOWER",
    title: "Renewable capacity expansion milestone",
    summary: "Additional clean energy capacity moved operational, improving long-term portfolio mix.",
    type: "filing",
    impact: "medium",
    timestamp: "2026-03-21T11:40:00+05:30",
    sourceLabel: "Exchange Disclosure",
    sourceUrl: "#",
    details: [
      "Generation mix tilt continues toward renewable assets with better long-run strategic optionality.",
      "Execution cadence supports confidence in stated commissioning timeline.",
      "Financing and tariff assumptions remain key variables for valuation sensitivity.",
    ],
  },
  {
    id: "timeline-5",
    company: "HDFCBANK",
    title: "Risk monitor flagged moderation in credit momentum",
    summary: "Internal trend monitor indicates slight moderation in disbursal growth versus prior month.",
    type: "signal",
    impact: "low",
    timestamp: "2026-03-21T09:10:00+05:30",
    sourceLabel: "Portfolio Risk Model",
    details: [
      "Signal is informational and not yet a structural deterioration flag.",
      "Deposit growth pace and cost of funds are critical for margin stability.",
      "Monitor next management commentary for updated growth confidence.",
    ],
  },
  {
    id: "timeline-6",
    company: "M&M",
    title: "EV lineup commentary improved narrative strength",
    summary: "Product roadmap update reinforced positioning in premium EV adoption cycles.",
    type: "news",
    impact: "medium",
    timestamp: "2026-03-20T18:15:00+05:30",
    sourceLabel: "Auto Sector Coverage",
    sourceUrl: "#",
    details: [
      "Narrative tailwind is positive, but execution and pricing remain crucial.",
      "Supply chain resilience may determine ability to capture demand spikes.",
      "Cross-impact expected for listed component suppliers.",
    ],
  },
];

interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  keywords: string;
  action: () => void;
}

interface NavItem {
  key: ViewKey;
  label: string;
  icon: typeof LayoutDashboard;
  caption: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, caption: "Overview" },
  { key: "chat", label: "Iris Chat", icon: Bot, caption: "Copilot" },
  { key: "discovery", label: "Discovery", icon: Compass, caption: "Themes" },
  { key: "portfolio", label: "Portfolio", icon: Wallet, caption: "Exposure" },
  { key: "filings", label: "Filings", icon: FileText, caption: "Reports" },
  { key: "timeline", label: "Timeline", icon: Clock3, caption: "Feed" },
  { key: "news", label: "News", icon: Newspaper, caption: "Sentiment" },
  { key: "settings", label: "Settings", icon: Settings, caption: "Preferences" },
];

const THEME_STORAGE_KEY = "equityai-theme";

type ViewTransitionCapable = {
  startViewTransition?: (updateCallback: () => void) => { finished: Promise<void> };
};

function getInitialTheme(): Theme {
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteActiveIndex, setPaletteActiveIndex] = useState(0);
  const paletteInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.classList.toggle("theme-dark", theme === "dark");
    root.classList.toggle("theme-light", theme === "light");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    const root = document.documentElement;
    const startViewTransition = (document as unknown as ViewTransitionCapable).startViewTransition;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const clearTransitionClass = () => {
      root.classList.remove("theme-transitioning");
    };
    const applyThemeToggle = () => {
      setTheme((current) => (current === "light" ? "dark" : "light"));
    };

    root.classList.add("theme-transitioning");

    if (!reducedMotion && typeof startViewTransition === "function") {
      try {
        const transition = startViewTransition(() => {
          applyThemeToggle();
        });

        if (transition && "finished" in transition) {
          transition.finished.finally(clearTransitionClass);
        } else {
          window.setTimeout(clearTransitionClass, 420);
        }
        return;
      } catch {
        applyThemeToggle();
        window.setTimeout(clearTransitionClass, 420);
        return;
      }
    }

    applyThemeToggle();
    window.setTimeout(() => {
      clearTransitionClass();
    }, 420);
  }, []);

  const goToView = useCallback((view: ViewKey) => {
    setActiveView(view);
    setPaletteOpen(false);
    setPaletteQuery("");
    setPaletteActiveIndex(0);
  }, []);

  const openPalette = useCallback(() => {
    setPaletteOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    setPaletteOpen(false);
    setPaletteQuery("");
    setPaletteActiveIndex(0);
  }, []);

  const paletteCommands = useMemo<CommandItem[]>(
    () => [
      {
        id: "go-dashboard",
        label: "Go to Dashboard",
        hint: "Navigation",
        keywords: "dashboard home overview",
        action: () => goToView("dashboard"),
      },
      {
        id: "go-chat",
        label: "Go to Iris Chat",
        hint: "Navigation",
        keywords: "chat copilot iris assistant",
        action: () => goToView("chat"),
      },
      {
        id: "go-discovery",
        label: "Go to Discovery",
        hint: "Navigation",
        keywords: "discovery themes ai defense sectors",
        action: () => goToView("discovery"),
      },
      {
        id: "go-portfolio",
        label: "Go to Portfolio",
        hint: "Navigation",
        keywords: "portfolio holdings risk exposure",
        action: () => goToView("portfolio"),
      },
      {
        id: "go-timeline",
        label: "Go to Timeline",
        hint: "Navigation",
        keywords: "timeline feed events filings history",
        action: () => goToView("timeline"),
      },
      {
        id: "go-filings",
        label: "Go to Filings",
        hint: "Navigation",
        keywords: "filings sec reports documents",
        action: () => goToView("filings"),
      },
      {
        id: "go-news",
        label: "Go to News & Sentiment",
        hint: "Navigation",
        keywords: "news sentiment headlines",
        action: () => goToView("news"),
      },
      {
        id: "go-settings",
        label: "Go to Settings",
        hint: "Navigation",
        keywords: "settings preferences configuration",
        action: () => goToView("settings"),
      },
      {
        id: "toggle-theme",
        label: theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme",
        hint: "Appearance",
        keywords: "theme light dark appearance",
        action: () => {
          toggleTheme();
          closePalette();
        },
      },
    ],
    [closePalette, goToView, theme, toggleTheme]
  );

  const filteredCommands = useMemo(() => {
    const query = paletteQuery.trim().toLowerCase();
    if (!query) return paletteCommands;

    return paletteCommands.filter((command) => {
      const haystack = `${command.label} ${command.keywords} ${command.hint ?? ""}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [paletteCommands, paletteQuery]);

  useEffect(() => {
    if (!paletteOpen) return;
    window.requestAnimationFrame(() => {
      paletteInputRef.current?.focus();
    });
  }, [paletteOpen]);

  useEffect(() => {
    setPaletteActiveIndex(0);
  }, [paletteQuery]);

  useEffect(() => {
    const handleGlobalShortcuts = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTypingContext =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
        return;
      }

      if (!paletteOpen) return;

      if (isTypingContext) {
        if (event.key === "Escape") {
          event.preventDefault();
          closePalette();
        }
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        closePalette();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setPaletteActiveIndex((current) =>
          filteredCommands.length ? (current + 1) % filteredCommands.length : 0
        );
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setPaletteActiveIndex((current) =>
          filteredCommands.length
            ? (current - 1 + filteredCommands.length) % filteredCommands.length
            : 0
        );
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        const command = filteredCommands[paletteActiveIndex];
        command?.action();
      }
    };

    window.addEventListener("keydown", handleGlobalShortcuts);
    return () => {
      window.removeEventListener("keydown", handleGlobalShortcuts);
    };
  }, [closePalette, filteredCommands, paletteActiveIndex, paletteOpen]);

  const page = useMemo(() => {
    switch (activeView) {
      case "dashboard":
        return <DashboardView />;
      case "chat":
        return <ChatView />;
      case "discovery":
        return <DiscoveryView />;
      case "portfolio":
        return <PortfolioView />;
      case "filings":
        return <FilingsView />;
      case "timeline":
        return <TimelineView />;
      case "news":
        return <NewsView />;
      case "settings":
        return <SettingsView theme={theme} onToggleTheme={toggleTheme} />;
      default:
        return <DashboardView />;
    }
  }, [activeView, theme, toggleTheme]);

  return (
    <div className="app-shell">
      <aside className="side-panel">
        <div className="brand-block">
          <div className="brand-mark">
            <Sparkles size={16} />
          </div>
          <div>
            <p className="brand-title">EquityAI</p>
            <p className="brand-subtitle">Research Console</p>
          </div>
        </div>

        <button type="button" className="theme-toggle" onClick={toggleTheme}>
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
          <span>{theme === "dark" ? "Switch to light" : "Switch to dark"}</span>
        </button>

        <button type="button" className="command-shortcut" onClick={openPalette}>
          <span className="command-shortcut-left">
            <Command size={14} />
            Command Palette
          </span>
          <span className="kbd-chip">Ctrl/Cmd + K</span>
        </button>

        <nav className="nav-stack">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setActiveView(item.key)}
                className={`nav-item ${isActive ? "active" : ""}`}
              >
                <span className="nav-icon">
                  <Icon size={16} />
                </span>
                <span className="nav-copy">
                  <span className="nav-label">{item.label}</span>
                  <span className="nav-caption">{item.caption}</span>
                </span>
              </button>
            );
          })}
        </nav>

        <div className="side-footer">
          <p className="status-label">System Health</p>
          <div className="status-pill">All services connected</div>
        </div>
      </aside>

      <main className="main-panel">{page}</main>

      {paletteOpen ? (
        <div className="command-overlay" role="dialog" aria-modal="true" aria-label="Command palette">
          <button type="button" className="command-backdrop" onClick={closePalette} />
          <div className="command-panel">
            <div className="command-input-row">
              <Search size={15} />
              <input
                ref={paletteInputRef}
                value={paletteQuery}
                onChange={(event) => setPaletteQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    const command = filteredCommands[paletteActiveIndex] ?? filteredCommands[0];
                    command?.action();
                    return;
                  }

                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    setPaletteActiveIndex((current) =>
                      filteredCommands.length ? (current + 1) % filteredCommands.length : 0
                    );
                    return;
                  }

                  if (event.key === "ArrowUp") {
                    event.preventDefault();
                    setPaletteActiveIndex((current) =>
                      filteredCommands.length
                        ? (current - 1 + filteredCommands.length) % filteredCommands.length
                        : 0
                    );
                    return;
                  }

                  if (event.key === "Escape") {
                    event.preventDefault();
                    closePalette();
                  }
                }}
                placeholder="Search commands, pages, and actions..."
              />
            </div>

            <div className="command-list" role="listbox" aria-activedescendant={filteredCommands[paletteActiveIndex]?.id}>
              {filteredCommands.length ? (
                filteredCommands.map((command, index) => (
                  <button
                    type="button"
                    key={command.id}
                    id={command.id}
                    role="option"
                    aria-selected={index === paletteActiveIndex}
                    className={`command-item ${index === paletteActiveIndex ? "active" : ""}`}
                    onMouseEnter={() => setPaletteActiveIndex(index)}
                    onClick={command.action}
                  >
                    <span>{command.label}</span>
                    <span>{command.hint ?? "Action"}</span>
                  </button>
                ))
              ) : (
                <p className="command-empty">No matching commands.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function PageHeader(props: { title: string; subtitle: string; right?: ReactNode }) {
  return (
    <header className="page-header">
      <div>
        <h1>{props.title}</h1>
        <p>{props.subtitle}</p>
      </div>
      {props.right ? <div>{props.right}</div> : null}
    </header>
  );
}

function DashboardView() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse>({});
  const [apiStatus, setApiStatus] = useState<ApiStatusResponse>({});
  const [headlines, setHeadlines] = useState<NewsDataResponse>({});
  const [holdingsCount, setHoldingsCount] = useState<number>(0);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);

    const [healthRes, apiRes, headlinesRes, holdingsRes] = await Promise.allSettled([
      fetchBackendHealth(),
      fetchApiStatus(),
      fetchMarketHeadlines(),
      fetchHoldingsCount(),
    ]);

    if (healthRes.status === "fulfilled") setHealth(healthRes.value);
    if (apiRes.status === "fulfilled") setApiStatus(apiRes.value);
    if (headlinesRes.status === "fulfilled") setHeadlines(headlinesRes.value);
    if (holdingsRes.status === "fulfilled") setHoldingsCount(holdingsRes.value);

    const failedCount = [healthRes, apiRes, headlinesRes, holdingsRes].filter(
      (result) => result.status === "rejected"
    ).length;

    if (failedCount === 4) {
      setError("Could not connect to backend services. Check server status.");
    } else if (failedCount > 0) {
      setError("Some widgets are unavailable right now.");
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  const headlineCount = headlines.results?.length ?? headlines.totalResults ?? 0;
  const latestHeadline = headlines.results?.[0]?.title ?? "No headlines yet";

  return (
    <section className="page-wrap">
      <PageHeader
        title="Market Command Center"
        subtitle="Track activity, spot risks, and jump into analysis flows quickly."
        right={
          <button type="button" className="primary-btn" onClick={() => void loadDashboardData()}>
            {loading ? "Refreshing..." : "Refresh Data"}
          </button>
        }
      />

      {error ? <div className="notice warning">{error}</div> : null}

      <div className="kpi-grid">
        <article className="kpi-card">
          <p>Portfolio Companies</p>
          <h2>{loading ? "--" : holdingsCount}</h2>
          <small>From Upstox holdings</small>
        </article>
        <article className="kpi-card">
          <p>Live Headlines</p>
          <h2>{loading ? "--" : headlineCount}</h2>
          <small>From NewsData market feed</small>
        </article>
        <article className="kpi-card">
          <p>Backend Health</p>
          <h2>{loading ? "--" : (health.status ?? "unknown")}</h2>
          <small>{health.message ?? "No status message"}</small>
        </article>
        <article className="kpi-card">
          <p>API Version</p>
          <h2>{loading ? "--" : (apiStatus.api_version ?? "n/a")}</h2>
          <small>Status: {apiStatus.status ?? "unknown"}</small>
        </article>
      </div>

      <div className="split-grid">
        <article className="feature-card">
          <div className="feature-head">
            <BarChart3 size={18} />
            <h3>Portfolio Concentration</h3>
          </div>
          <p>
            Top 3 positions account for 47% of capital. Consider rebalancing to reduce concentration risk.
          </p>
        </article>
        <article className="feature-card">
          <div className="feature-head">
            <TrendingUp size={18} />
            <h3>Latest Market Headline</h3>
          </div>
          <p>{loading ? "Loading latest headline..." : latestHeadline}</p>
        </article>
      </div>
    </section>
  );
}

function ChatView() {
  return (
    <section className="page-wrap">
      <PageHeader
        title="Iris Research Copilot"
        subtitle="Ask focused questions across filings, portfolio, and market sentiment."
      />

      <article className="chat-shell">
        <div className="chat-messages">
          <div className="message assistant">
            <p>
              I can help compare companies, summarize filings, and explain market moves in plain language.
            </p>
          </div>
          <div className="message user">
            <p>Summarize major risk signals for my top holdings this week.</p>
          </div>
        </div>

        <div className="chat-input-row">
          <input placeholder="Ask Iris anything about equities..." />
          <button className="primary-btn">Send</button>
        </div>
      </article>
    </section>
  );
}

function DiscoveryView() {
  const [query, setQuery] = useState("");
  const [activeTheme, setActiveTheme] = useState<string>("all");
  const [activeSector, setActiveSector] = useState<string>("all");
  const [marketCapBucket, setMarketCapBucket] = useState<MarketCapBucket>("all");
  const [minThemeScore, setMinThemeScore] = useState<number>(60);

  const allThemes = useMemo(() => {
    const set = new Set<string>();
    for (const company of DISCOVERY_COMPANIES) {
      for (const theme of Object.keys(company.themeScores)) {
        set.add(theme);
      }
    }
    return ["all", ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, []);

  const allSectors = useMemo(() => {
    const set = new Set(DISCOVERY_COMPANIES.map((company) => company.sector));
    return ["all", ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, []);

  const filteredCompanies = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return DISCOVERY_COMPANIES.filter((company) => {
      const maxThemeScore = Math.max(...Object.values(company.themeScores));

      const matchesQuery =
        !normalizedQuery ||
        `${company.symbol} ${company.name} ${company.sector} ${company.insight}`
          .toLowerCase()
          .includes(normalizedQuery);

      const matchesTheme =
        activeTheme === "all" || (company.themeScores[activeTheme] ?? 0) >= minThemeScore;

      const matchesSector = activeSector === "all" || company.sector === activeSector;

      const matchesMarketCap =
        marketCapBucket === "all" ||
        (marketCapBucket === "mega" && company.marketCapBn >= 120) ||
        (marketCapBucket === "large" && company.marketCapBn >= 40 && company.marketCapBn < 120) ||
        (marketCapBucket === "mid" && company.marketCapBn >= 10 && company.marketCapBn < 40) ||
        (marketCapBucket === "small" && company.marketCapBn < 10);

      const matchesMinimumThemeScore = maxThemeScore >= minThemeScore;

      return (
        matchesQuery &&
        matchesTheme &&
        matchesSector &&
        matchesMarketCap &&
        matchesMinimumThemeScore
      );
    }).sort((a, b) => {
      const aTop = Math.max(...Object.values(a.themeScores));
      const bTop = Math.max(...Object.values(b.themeScores));
      return bTop - aTop;
    });
  }, [activeSector, activeTheme, marketCapBucket, minThemeScore, query]);

  const summaryText = useMemo(() => {
    if (!filteredCompanies.length) return "No companies match current discovery filters.";
    const top = filteredCompanies[0];
    const [topTheme, topScore] = Object.entries(top.themeScores).sort((a, b) => b[1] - a[1])[0];
    return `${filteredCompanies.length} companies matched. Top signal: ${top.symbol} in ${topTheme} (${topScore}/100).`;
  }, [filteredCompanies]);

  return (
    <section className="page-wrap">
      <PageHeader
        title="Thematic Discovery Engine"
        subtitle="Discover companies by AI-native themes, sector relevance, and conviction scores."
      />

      <div className="discovery-panel">
        <div className="search-pill discovery-search">
          <Search size={14} />
          <input
            placeholder="Search AI companies, defense, EV, fintech..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>

        <div className="discovery-controls">
          <select
            className="type-select"
            value={activeTheme}
            onChange={(event) => setActiveTheme(event.target.value)}
          >
            {allThemes.map((theme) => (
              <option key={theme} value={theme}>
                Theme: {theme === "all" ? "All" : theme}
              </option>
            ))}
          </select>

          <select
            className="type-select"
            value={activeSector}
            onChange={(event) => setActiveSector(event.target.value)}
          >
            {allSectors.map((sector) => (
              <option key={sector} value={sector}>
                Sector: {sector === "all" ? "All" : sector}
              </option>
            ))}
          </select>

          <select
            className="type-select"
            value={marketCapBucket}
            onChange={(event) => setMarketCapBucket(event.target.value as MarketCapBucket)}
          >
            <option value="all">Market Cap: All</option>
            <option value="mega">Mega (&gt;= 120B)</option>
            <option value="large">Large (40-120B)</option>
            <option value="mid">Mid (10-40B)</option>
            <option value="small">Small (&lt; 10B)</option>
          </select>
        </div>

        <div className="discovery-score-row">
          <label htmlFor="theme-score" className="results-title">
            Minimum Theme Score: {minThemeScore}
          </label>
          <input
            id="theme-score"
            type="range"
            min={40}
            max={95}
            step={1}
            value={minThemeScore}
            onChange={(event) => setMinThemeScore(Number(event.target.value))}
            className="score-slider"
          />
        </div>
      </div>

      <div className="notice">{summaryText}</div>

      <div className="discovery-grid">
        {filteredCompanies.length ? (
          filteredCompanies.map((company) => {
            const sortedThemes = Object.entries(company.themeScores)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4);

            return (
              <article key={company.symbol} className="discovery-card">
                <div className="discovery-card-head">
                  <div>
                    <p className="discovery-symbol">{company.symbol}</p>
                    <h3>{company.name}</h3>
                  </div>
                  <span className="chip">${company.marketCapBn.toFixed(1)}B</span>
                </div>

                <p className="discovery-sector">{company.sector}</p>
                <p className="discovery-insight">{company.insight}</p>

                <div className="chip-row discovery-chips">
                  {sortedThemes.map(([theme, score]) => (
                    <span key={`${company.symbol}-${theme}`} className="chip discovery-theme-chip">
                      {theme} · {score}
                    </span>
                  ))}
                </div>
              </article>
            );
          })
        ) : (
          <div className="list-item single-line">
            <p>No discovery matches. Try lowering score or widening filters.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function PortfolioView() {
  return (
    <section className="page-wrap">
      <PageHeader
        title="Portfolio Intelligence"
        subtitle="Exposure, risk concentration, and opportunity signals at a glance."
      />

      <div className="table-card">
        <div className="table-head">
          <h3>Top Holdings</h3>
          <span>Updated now</span>
        </div>
        <div className="table-row">
          <span>RELIANCE</span>
          <span>22.4%</span>
          <span className="positive">+2.8%</span>
        </div>
        <div className="table-row">
          <span>TCS</span>
          <span>14.1%</span>
          <span className="positive">+1.2%</span>
        </div>
        <div className="table-row">
          <span>HDFCBANK</span>
          <span>10.9%</span>
          <span className="negative">-0.6%</span>
        </div>
      </div>
    </section>
  );
}

function TimelineView() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | TimelineEvent["type"]>("all");
  const [impactFilter, setImpactFilter] = useState<"all" | TimelineEvent["impact"]>("all");
  const [selectedEventId, setSelectedEventId] = useState<string>(TIMELINE_EVENTS[0]?.id ?? "");

  const filteredEvents = useMemo(() => {
    const normalized = query.trim().toLowerCase();

    return TIMELINE_EVENTS.filter((event) => {
      const matchesQuery =
        !normalized ||
        `${event.company} ${event.title} ${event.summary} ${event.sourceLabel}`
          .toLowerCase()
          .includes(normalized);

      const matchesType = typeFilter === "all" || event.type === typeFilter;
      const matchesImpact = impactFilter === "all" || event.impact === impactFilter;

      return matchesQuery && matchesType && matchesImpact;
    }).sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [impactFilter, query, typeFilter]);

  useEffect(() => {
    if (!filteredEvents.length) {
      setSelectedEventId("");
      return;
    }

    const exists = filteredEvents.some((event) => event.id === selectedEventId);
    if (!exists) {
      setSelectedEventId(filteredEvents[0].id);
    }
  }, [filteredEvents, selectedEventId]);

  const selectedEvent = filteredEvents.find((event) => event.id === selectedEventId) ?? null;

  const formatTimestamp = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  };

  const getTypeClass = (type: TimelineEvent["type"]) => {
    if (type === "filing") return "chip type-filing";
    if (type === "news") return "chip type-news";
    return "chip type-signal";
  };

  const getImpactClass = (impact: TimelineEvent["impact"]) => {
    if (impact === "high") return "chip negative";
    if (impact === "medium") return "chip warning";
    return "chip positive";
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Research Timeline Feed"
        subtitle="Chronological filing and insight stream with quick detail drill-down."
      />

      <div className="timeline-toolbar">
        <div className="search-pill timeline-search">
          <Search size={14} />
          <input
            placeholder="Search company, event, or source..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>

        <div className="chip-row">
          <select
            className="type-select"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value as "all" | TimelineEvent["type"])}
          >
            <option value="all">Type: All</option>
            <option value="filing">Type: Filing</option>
            <option value="news">Type: News</option>
            <option value="signal">Type: Signal</option>
          </select>

          <select
            className="type-select"
            value={impactFilter}
            onChange={(event) =>
              setImpactFilter(event.target.value as "all" | TimelineEvent["impact"])
            }
          >
            <option value="all">Impact: All</option>
            <option value="high">Impact: High</option>
            <option value="medium">Impact: Medium</option>
            <option value="low">Impact: Low</option>
          </select>
        </div>
      </div>

      <div className="timeline-layout">
        <div className="timeline-list">
          {filteredEvents.length ? (
            filteredEvents.map((event) => (
              <button
                key={event.id}
                type="button"
                className={`timeline-item ${selectedEventId === event.id ? "active" : ""}`}
                onClick={() => setSelectedEventId(event.id)}
              >
                <div className="timeline-item-head">
                  <p>{event.company}</p>
                  <span>{formatTimestamp(event.timestamp)}</span>
                </div>
                <h3>{event.title}</h3>
                <p>{event.summary}</p>
                <div className="chip-row timeline-item-chips">
                  <span className={getTypeClass(event.type)}>{event.type}</span>
                  <span className={getImpactClass(event.impact)}>{event.impact} impact</span>
                </div>
              </button>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No timeline events match the current filters.</p>
            </div>
          )}
        </div>

        <aside className="timeline-detail">
          {selectedEvent ? (
            <>
              <div className="timeline-detail-head">
                <div>
                  <p className="discovery-symbol">{selectedEvent.company}</p>
                  <h3>{selectedEvent.title}</h3>
                </div>
                <span className="chip">{formatTimestamp(selectedEvent.timestamp)}</span>
              </div>

              <p className="discovery-insight">{selectedEvent.summary}</p>

              <div className="chip-row timeline-item-chips">
                <span className={getTypeClass(selectedEvent.type)}>{selectedEvent.type}</span>
                <span className={getImpactClass(selectedEvent.impact)}>
                  {selectedEvent.impact} impact
                </span>
                <span className="chip">{selectedEvent.sourceLabel}</span>
              </div>

              <div className="timeline-bullets">
                {selectedEvent.details.map((detail, index) => (
                  <p key={`${selectedEvent.id}-detail-${index}`}>{detail}</p>
                ))}
              </div>

              {selectedEvent.sourceUrl ? (
                <a href={selectedEvent.sourceUrl} target="_blank" rel="noreferrer" className="secondary-btn timeline-link">
                  Open Source Reference
                </a>
              ) : null}
            </>
          ) : (
            <div className="list-item single-line">
              <p>Select an event to view details.</p>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}

function FilingsView() {
  const [symbolInput, setSymbolInput] = useState("AAPL");
  const [activeSymbol, setActiveSymbol] = useState("AAPL");
  const [filingType, setFilingType] = useState("");

  const [filings, setFilings] = useState<SecFiling[]>([]);
  const [searchResults, setSearchResults] = useState<CompanySearchResult[]>([]);

  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadFilings = useCallback(async (symbol: string, selectedType?: string) => {
    setLoading(true);
    setError(null);

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
  }, []);

  useEffect(() => {
    void loadFilings(activeSymbol, filingType || undefined);
  }, [activeSymbol, filingType, loadFilings]);

  const handleSearch = useCallback(async () => {
    const query = symbolInput.trim();
    if (!query) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    setSearchError(null);

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
  }, [symbolInput]);

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
            <option value="10-K">10-K</option>
            <option value="10-Q">10-Q</option>
            <option value="8-K">8-K</option>
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
        {loading ? <div className="list-item single-line"><p>Loading filings...</p></div> : null}

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
                <p>
                  {(filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`)}
                </p>
                <span>{formatFilingDate(filing.filingDate ?? filing.acceptedDate)}</span>
              </a>
            ))
          : null}
      </div>
    </section>
  );
}

function NewsView() {
  const [symbolInput, setSymbolInput] = useState("RELIANCE");
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");

  const [headlines, setHeadlines] = useState<NewsDataResponse>({});
  const [sentimentFeed, setSentimentFeed] = useState<SentimentFeedResponse | null>(null);

  const [loadingHeadlines, setLoadingHeadlines] = useState(true);
  const [loadingSentiment, setLoadingSentiment] = useState(true);

  const [headlinesError, setHeadlinesError] = useState<string | null>(null);
  const [sentimentError, setSentimentError] = useState<string | null>(null);

  const loadHeadlines = useCallback(async () => {
    setLoadingHeadlines(true);
    setHeadlinesError(null);

    try {
      const data = await fetchMarketHeadlines();
      setHeadlines(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setHeadlinesError("News API is not configured on backend yet (401).");
      } else {
        setHeadlinesError("Could not load market headlines.");
      }
    } finally {
      setLoadingHeadlines(false);
    }
  }, []);

  const loadSentiment = useCallback(async (symbol: string) => {
    setLoadingSentiment(true);
    setSentimentError(null);

    try {
      const data = await fetchTickerSentiment(symbol, 24, 8);
      setSentimentFeed(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setSentimentError("Sentiment feed is unauthorized until backend keys are configured.");
      } else {
        setSentimentError(`Could not load sentiment for ${symbol}.`);
      }
      setSentimentFeed(null);
    } finally {
      setLoadingSentiment(false);
    }
  }, []);

  useEffect(() => {
    void loadHeadlines();
  }, [loadHeadlines]);

  useEffect(() => {
    void loadSentiment(activeSymbol);
  }, [activeSymbol, loadSentiment]);

  const sentimentCounts = {
    positive:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "positive").length ?? 0,
    neutral:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "neutral").length ?? 0,
    negative:
      sentimentFeed?.articles.filter((item) => item.sentiment?.toLowerCase() === "negative").length ?? 0,
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="News & Sentiment Radar"
        subtitle="Monitor market narratives and detect sector-level shifts quickly."
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              const normalized = symbolInput.trim().toUpperCase();
              if (normalized) {
                setActiveSymbol(normalized);
              }
            }}
          >
            <Search size={14} />
            <input
              placeholder="Ticker symbol"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
            />
          </form>
        }
      />

      <div className="news-toolbar">
        <div className="chip-row">
          <span className="chip">Ticker: {activeSymbol}</span>
          <span className="chip">Headlines: {headlines.results?.length ?? 0}</span>
          <span className="chip">Sentiment: {sentimentFeed?.total_results ?? 0}</span>
        </div>
        <div className="chip-row">
          <button type="button" className="secondary-btn mini-btn" onClick={() => void loadHeadlines()}>
            Refresh Headlines
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => void loadSentiment(activeSymbol)}
          >
            Refresh Sentiment
          </button>
        </div>
      </div>

      {headlinesError ? <div className="notice warning">{headlinesError}</div> : null}
      {sentimentError ? <div className="notice warning">{sentimentError}</div> : null}

      <div className="split-grid">
        <article className="feature-card news-panel">
          <div className="feature-head">
            <Newspaper size={18} />
            <h3>Top Headlines</h3>
          </div>

          {loadingHeadlines ? (
            <p>Loading market headlines...</p>
          ) : (
            <div className="feed-list">
              {(headlines.results ?? []).slice(0, 8).map((article, index) => (
                <a
                  key={`${article.article_id ?? article.link ?? index}`}
                  href={article.link ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="feed-item"
                >
                  <p>{article.title ?? "Untitled headline"}</p>
                  <span>
                    {article.source_name ?? "Unknown source"}
                    {article.pubDate ? ` · ${article.pubDate}` : ""}
                  </span>
                </a>
              ))}
              {!(headlines.results ?? []).length ? (
                <p>No headlines available for now.</p>
              ) : null}
            </div>
          )}
        </article>

        <article className="feature-card news-panel">
          <div className="feature-head">
            <TrendingUp size={18} />
            <h3>Sentiment Feed ({activeSymbol})</h3>
          </div>

          <div className="chip-row sentiment-row">
            <span className="chip positive">Positive: {sentimentCounts.positive}</span>
            <span className="chip">Neutral: {sentimentCounts.neutral}</span>
            <span className="chip negative">Negative: {sentimentCounts.negative}</span>
          </div>

          {loadingSentiment ? (
            <p>Loading sentiment feed...</p>
          ) : (
            <div className="feed-list">
              {(sentimentFeed?.articles ?? []).slice(0, 8).map((article, index) => (
                <a
                  key={`${article.article_id ?? article.link ?? index}`}
                  href={article.link ?? "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="feed-item"
                >
                  <p>{article.title ?? "Untitled article"}</p>
                  <span>
                    {article.sentiment ?? "unknown"}
                    {article.source_name ? ` · ${article.source_name}` : ""}
                  </span>
                </a>
              ))}
              {!(sentimentFeed?.articles ?? []).length ? (
                <p>No sentiment articles available for this symbol.</p>
              ) : null}
            </div>
          )}
        </article>
      </div>
    </section>
  );
}

function SettingsView(props: { theme: Theme; onToggleTheme: () => void }) {
  return (
    <section className="page-wrap">
      <PageHeader
        title="Workspace Settings"
        subtitle="Configure integrations, notifications, and assistant preferences."
      />

      <div className="list-card">
        <div className="list-item">
          <p>API Integrations</p>
          <span>Configured</span>
        </div>
        <div className="list-item">
          <p>Notification Rules</p>
          <span>3 active</span>
        </div>
        <div className="list-item">
          <p>Theme & Layout</p>
          <span>{props.theme === "dark" ? "Aesthetic Dark" : "Modern Light"}</span>
        </div>
      </div>

      <button type="button" className="secondary-btn" onClick={props.onToggleTheme}>
        {props.theme === "dark" ? "Use Light Mode" : "Use Dark Mode"}
      </button>
    </section>
  );
}
