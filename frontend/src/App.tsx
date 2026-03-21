import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  BarChart3,
  Bot,
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

type ViewKey = "dashboard" | "chat" | "portfolio" | "filings" | "news" | "settings";
type Theme = "light" | "dark";

interface NavItem {
  key: ViewKey;
  label: string;
  icon: typeof LayoutDashboard;
  caption: string;
}

const navItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, caption: "Overview" },
  { key: "chat", label: "Iris Chat", icon: Bot, caption: "Copilot" },
  { key: "portfolio", label: "Portfolio", icon: Wallet, caption: "Exposure" },
  { key: "filings", label: "Filings", icon: FileText, caption: "Reports" },
  { key: "news", label: "News", icon: Newspaper, caption: "Sentiment" },
  { key: "settings", label: "Settings", icon: Settings, caption: "Preferences" },
];

const THEME_STORAGE_KEY = "equityai-theme";

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

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === "light" ? "dark" : "light"));
  }, []);

  const page = useMemo(() => {
    switch (activeView) {
      case "dashboard":
        return <DashboardView />;
      case "chat":
        return <ChatView />;
      case "portfolio":
        return <PortfolioView />;
      case "filings":
        return <FilingsView />;
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
  return (
    <section className="page-wrap">
      <PageHeader
        title="Market Command Center"
        subtitle="Track activity, spot risks, and jump into analysis flows quickly."
        right={<button className="primary-btn">Create Brief</button>}
      />

      <div className="kpi-grid">
        <article className="kpi-card">
          <p>Portfolio Companies</p>
          <h2>18</h2>
          <small>+2 since last week</small>
        </article>
        <article className="kpi-card">
          <p>Filings Processed</p>
          <h2>126</h2>
          <small>Last 24 hours</small>
        </article>
        <article className="kpi-card">
          <p>Sentiment Pulse</p>
          <h2>Moderate Bullish</h2>
          <small>Based on 92 articles</small>
        </article>
        <article className="kpi-card">
          <p>Iris Sessions</p>
          <h2>42</h2>
          <small>Today</small>
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
            <h3>Theme Momentum</h3>
          </div>
          <p>
            Renewables and defense appear in 32% of recent filings. Momentum remains strong across mid-cap names.
          </p>
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

function FilingsView() {
  return (
    <section className="page-wrap">
      <PageHeader
        title="Filings Tracker"
        subtitle="Review latest results, corporate updates, and disclosure trends."
        right={
          <div className="search-pill">
            <Search size={14} />
            <input placeholder="Search ticker" />
          </div>
        }
      />

      <div className="list-card">
        <div className="list-item">
          <p>INFY - Quarterly Results Update</p>
          <span>2h ago</span>
        </div>
        <div className="list-item">
          <p>LT - Investor Presentation</p>
          <span>4h ago</span>
        </div>
        <div className="list-item">
          <p>ITC - Board Meeting Outcome</p>
          <span>7h ago</span>
        </div>
      </div>
    </section>
  );
}

function NewsView() {
  return (
    <section className="page-wrap">
      <PageHeader
        title="News & Sentiment Radar"
        subtitle="Monitor market narratives and detect sector-level shifts quickly."
      />

      <div className="split-grid">
        <article className="feature-card">
          <div className="feature-head">
            <Newspaper size={18} />
            <h3>Top Headlines</h3>
          </div>
          <p>Energy and banking dominate market coverage with positive earnings commentary.</p>
        </article>
        <article className="feature-card">
          <div className="feature-head">
            <TrendingUp size={18} />
            <h3>Sentiment Index</h3>
          </div>
          <p>Current reading 64/100. Strongest positivity from capital goods and industrials.</p>
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
