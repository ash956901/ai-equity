import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ArrowUpRight,
  BarChart3,
  Bell,
  Bookmark,
  BookmarkCheck,
  Building2,
  BookOpenText,
  Bot,
  CheckCheck,
  Clock3,
  Compass,
  Command,
  FileText,
  Flame,
  LayoutDashboard,
  Moon,
  Newspaper,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  Sun,
  TrendingUp,
  Trash2,
  Wallet,
  WandSparkles,
  X,
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
  | "company"
  | "discovery"
  | "portfolio"
  | "filings"
  | "timeline"
  | "news"
  | "settings";
type Theme = "light" | "dark";
type DashboardDensity = "comfortable" | "compact";

interface DashboardPreferences {
  density: DashboardDensity;
  hiddenWidgets: string[];
}

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

type NotificationCategory = "filing" | "risk" | "theme" | "system";
type NotificationSeverity = "high" | "medium" | "low";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  timestamp: string;
  read: boolean;
}

type ToastTone = "info" | "success" | "warning";

type ExplanationMode = "analyst" | "simple";

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  sources?: string[];
}

interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

interface SearchSelection {
  stamp: number;
  companySymbol?: string;
  discoveryQuery?: string;
  discoveryTheme?: string;
  filingsSymbol?: string;
  newsSymbol?: string;
  timelineQuery?: string;
  timelineEventId?: string;
  chatPrompt?: string;
}

type FavoriteType = "company" | "filing" | "headline";

interface FavoriteItem {
  id: string;
  type: FavoriteType;
  symbol?: string;
  title: string;
  subtitle?: string;
  url?: string;
  createdAt: string;
}

type ReportSectionId = "summary" | "risks" | "financials" | "themes";

interface ReportSectionOption {
  id: ReportSectionId;
  label: string;
}

interface DashboardWidget {
  id: string;
  label: string;
}

type AlertRuleType = "filing_event" | "risk_beta_above" | "theme_score_above";

interface AlertRule {
  id: string;
  name: string;
  type: AlertRuleType;
  symbol: string;
  threshold?: number;
  enabled: boolean;
  createdAt: string;
  lastCheckedAt?: string;
  lastTriggeredAt?: string;
}

interface PortfolioHolding {
  symbol: string;
  company: string;
  sector: string;
  weight: number;
  returnPct: number;
  beta: number;
  pe: number;
  pb: number;
  volatility: number;
}

type GlobalSearchResultType = "company" | "theme" | "event" | "query";

interface GlobalSearchResult {
  id: string;
  type: GlobalSearchResultType;
  title: string;
  subtitle: string;
  onSelect: () => void;
}

const QUICK_QUERY_TEMPLATES = [
  "Summarize the latest filing impact for RELIANCE.",
  "Explain top portfolio risks in simple language.",
  "Compare sentiment momentum: TCS vs INFY.",
  "What changed in defense theme this week?",
  "Give a 5-point summary for my timeline events.",
  "Which themes look overheated right now?",
];

const DASHBOARD_WIDGETS: DashboardWidget[] = [
  { id: "kpi-portfolio", label: "Portfolio Companies" },
  { id: "kpi-headlines", label: "Live Headlines" },
  { id: "kpi-health", label: "Backend Health" },
  { id: "kpi-api", label: "API Version" },
  { id: "feature-concentration", label: "Portfolio Concentration" },
  { id: "feature-headline", label: "Latest Market Headline" },
];

const REPORT_SECTION_OPTIONS: ReportSectionOption[] = [
  { id: "summary", label: "Executive Summary" },
  { id: "risks", label: "Key Risks" },
  { id: "financials", label: "Financial Snapshot" },
  { id: "themes", label: "Theme Outlook" },
];

const PORTFOLIO_HOLDINGS: PortfolioHolding[] = [
  {
    symbol: "RELIANCE",
    company: "Reliance Industries",
    sector: "Energy & Conglomerate",
    weight: 22.4,
    returnPct: 2.8,
    beta: 1.08,
    pe: 23.5,
    pb: 2.2,
    volatility: 18.4,
  },
  {
    symbol: "TCS",
    company: "Tata Consultancy Services",
    sector: "IT Services",
    weight: 14.1,
    returnPct: 1.2,
    beta: 0.84,
    pe: 27.4,
    pb: 11.5,
    volatility: 14.9,
  },
  {
    symbol: "HDFCBANK",
    company: "HDFC Bank",
    sector: "Banking",
    weight: 10.9,
    returnPct: -0.6,
    beta: 0.92,
    pe: 18.1,
    pb: 2.9,
    volatility: 16.2,
  },
  {
    symbol: "HAL",
    company: "Hindustan Aeronautics",
    sector: "Defense",
    weight: 9.2,
    returnPct: 3.4,
    beta: 1.16,
    pe: 31.2,
    pb: 8.1,
    volatility: 25.4,
  },
  {
    symbol: "TATAPOWER",
    company: "Tata Power",
    sector: "Utilities",
    weight: 8.5,
    returnPct: 1.9,
    beta: 1.22,
    pe: 24.6,
    pb: 3.6,
    volatility: 22.1,
  },
  {
    symbol: "M&M",
    company: "Mahindra & Mahindra",
    sector: "Automotive",
    weight: 7.8,
    returnPct: 0.7,
    beta: 1.03,
    pe: 26.3,
    pb: 3.4,
    volatility: 19.8,
  },
];

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

const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-1",
    title: "New filing detected for RELIANCE",
    message: "Quarterly update added to feed. Review margin and capex commentary.",
    category: "filing",
    severity: "high",
    timestamp: "2026-03-21T19:15:00+05:30",
    read: false,
  },
  {
    id: "notif-2",
    title: "Portfolio risk signal changed",
    message: "Your risk monitor moved from stable to watch for one banking position.",
    category: "risk",
    severity: "medium",
    timestamp: "2026-03-21T16:00:00+05:30",
    read: false,
  },
  {
    id: "notif-3",
    title: "Theme momentum alert: Defense",
    message: "Defense theme score crossed 90 in discovery engine for 2 tracked companies.",
    category: "theme",
    severity: "medium",
    timestamp: "2026-03-21T14:10:00+05:30",
    read: true,
  },
  {
    id: "notif-4",
    title: "System sync completed",
    message: "Local cache refreshed successfully. Data sources are ready for the next run.",
    category: "system",
    severity: "low",
    timestamp: "2026-03-21T09:30:00+05:30",
    read: true,
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
  { key: "company", label: "Company", icon: Building2, caption: "Workspace" },
  { key: "chat", label: "Iris Chat", icon: Bot, caption: "Copilot" },
  { key: "discovery", label: "Discovery", icon: Compass, caption: "Themes" },
  { key: "portfolio", label: "Portfolio", icon: Wallet, caption: "Exposure" },
  { key: "filings", label: "Filings", icon: FileText, caption: "Reports" },
  { key: "timeline", label: "Timeline", icon: Clock3, caption: "Feed" },
  { key: "news", label: "News", icon: Newspaper, caption: "Sentiment" },
  { key: "settings", label: "Settings", icon: Settings, caption: "Preferences" },
];

const THEME_STORAGE_KEY = "equityai-theme";
const NOTIFICATIONS_STORAGE_KEY = "equityai-notifications";
const FAVORITES_STORAGE_KEY = "equityai-favorites";
const DASHBOARD_PREFERENCES_KEY = "equityai-dashboard-preferences";
const ALERT_RULES_STORAGE_KEY = "equityai-alert-rules";

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

function getInitialNotifications(): NotificationItem[] {
  const saved = window.localStorage.getItem(NOTIFICATIONS_STORAGE_KEY);
  if (!saved) return DEFAULT_NOTIFICATIONS;

  try {
    const parsed = JSON.parse(saved) as NotificationItem[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return DEFAULT_NOTIFICATIONS;
  } catch {
    return DEFAULT_NOTIFICATIONS;
  }
}

function getInitialFavorites(): FavoriteItem[] {
  const saved = window.localStorage.getItem(FAVORITES_STORAGE_KEY);
  if (!saved) return [];

  try {
    const parsed = JSON.parse(saved) as FavoriteItem[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

function getInitialDashboardPreferences(): DashboardPreferences {
  const saved = window.localStorage.getItem(DASHBOARD_PREFERENCES_KEY);
  if (!saved) {
    return {
      density: "comfortable",
      hiddenWidgets: [],
    };
  }

  try {
    const parsed = JSON.parse(saved) as DashboardPreferences;
    if (parsed && (parsed.density === "comfortable" || parsed.density === "compact")) {
      return {
        density: parsed.density,
        hiddenWidgets: Array.isArray(parsed.hiddenWidgets) ? parsed.hiddenWidgets : [],
      };
    }
    return { density: "comfortable", hiddenWidgets: [] };
  } catch {
    return { density: "comfortable", hiddenWidgets: [] };
  }
}

function getInitialAlertRules(): AlertRule[] {
  const saved = window.localStorage.getItem(ALERT_RULES_STORAGE_KEY);
  if (!saved) {
    return [
      {
        id: "rule-1",
        name: "Reliance filing updates",
        type: "filing_event",
        symbol: "RELIANCE",
        enabled: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: "rule-2",
        name: "Portfolio beta guardrail",
        type: "risk_beta_above",
        symbol: "PORTFOLIO",
        threshold: 1.1,
        enabled: true,
        createdAt: new Date().toISOString(),
      },
      {
        id: "rule-3",
        name: "Defense theme momentum",
        type: "theme_score_above",
        symbol: "HAL",
        threshold: 90,
        enabled: false,
        createdAt: new Date().toISOString(),
      },
    ];
  }

  try {
    const parsed = JSON.parse(saved) as AlertRule[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [dashboardPreferences, setDashboardPreferences] =
    useState<DashboardPreferences>(getInitialDashboardPreferences);
  const [searchSelection, setSearchSelection] = useState<SearchSelection | null>(null);
  const [favorites, setFavorites] = useState<FavoriteItem[]>(getInitialFavorites);
  const [alertRules, setAlertRules] = useState<AlertRule[]>(getInitialAlertRules);
  const [favoritesOpen, setFavoritesOpen] = useState(false);
  const [favoriteFilter, setFavoriteFilter] = useState<"all" | FavoriteType>("all");
  const [notifications, setNotifications] = useState<NotificationItem[]>(getInitialNotifications);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationFilter, setNotificationFilter] = useState<"all" | NotificationCategory>("all");
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [alertRulesOpen, setAlertRulesOpen] = useState(false);
  const [ruleName, setRuleName] = useState("");
  const [ruleType, setRuleType] = useState<AlertRuleType>("filing_event");
  const [ruleSymbol, setRuleSymbol] = useState("RELIANCE");
  const [ruleThreshold, setRuleThreshold] = useState("1.1");
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [globalSearchIndex, setGlobalSearchIndex] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteActiveIndex, setPaletteActiveIndex] = useState(0);
  const paletteInputRef = useRef<HTMLInputElement | null>(null);
  const globalSearchInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.classList.toggle("theme-dark", theme === "dark");
    root.classList.toggle("theme-light", theme === "light");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(NOTIFICATIONS_STORAGE_KEY, JSON.stringify(notifications));
  }, [notifications]);

  useEffect(() => {
    window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    window.localStorage.setItem(ALERT_RULES_STORAGE_KEY, JSON.stringify(alertRules));
  }, [alertRules]);

  useEffect(() => {
    window.localStorage.setItem(
      DASHBOARD_PREFERENCES_KEY,
      JSON.stringify(dashboardPreferences)
    );
  }, [dashboardPreferences]);

  const unreadCount = useMemo(
    () => notifications.filter((notification) => !notification.read).length,
    [notifications]
  );

  const filteredNotifications = useMemo(
    () =>
      notifications.filter(
        (notification) =>
          notificationFilter === "all" || notification.category === notificationFilter
      ),
    [notificationFilter, notifications]
  );

  const filteredFavorites = useMemo(
    () =>
      favorites.filter((favorite) =>
        favoriteFilter === "all" ? true : favorite.type === favoriteFilter
      ),
    [favoriteFilter, favorites]
  );

  const activeRulesCount = useMemo(
    () => alertRules.filter((rule) => rule.enabled).length,
    [alertRules]
  );

  const pushToast = useCallback((message: string, tone: ToastTone = "info") => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((current) => [...current, { id, message, tone }]);

    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 3200);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const markAllNotificationsRead = useCallback(() => {
    setNotifications((current) => current.map((notification) => ({ ...notification, read: true })));
    pushToast("All notifications marked as read", "success");
  }, [pushToast]);

  const markNotificationRead = useCallback((id: string) => {
    setNotifications((current) =>
      current.map((notification) =>
        notification.id === id ? { ...notification, read: true } : notification
      )
    );
    pushToast("Notification marked as read", "success");
  }, [pushToast]);

  const dismissNotification = useCallback((id: string) => {
    setNotifications((current) => current.filter((notification) => notification.id !== id));
    pushToast("Notification dismissed", "info");
  }, [pushToast]);

  const addFavorite = useCallback(
    (favorite: Omit<FavoriteItem, "id" | "createdAt">) => {
      const key = `${favorite.type}::${favorite.title}::${favorite.symbol ?? ""}`.toLowerCase();

      setFavorites((current) => {
        const exists = current.some(
          (item) => `${item.type}::${item.title}::${item.symbol ?? ""}`.toLowerCase() === key
        );

        if (exists) {
          pushToast("Already in favorites", "info");
          return current;
        }

        const next: FavoriteItem = {
          ...favorite,
          id: `fav-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          createdAt: new Date().toISOString(),
        };

        pushToast("Saved to favorites", "success");
        return [next, ...current].slice(0, 120);
      });
    },
    [pushToast]
  );

  const removeFavorite = useCallback(
    (id: string) => {
      setFavorites((current) => current.filter((item) => item.id !== id));
      pushToast("Removed from favorites", "info");
    },
    [pushToast]
  );

  const isFavorited = useCallback(
    (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => {
      const key = `${favorite.type}::${favorite.title}::${favorite.symbol ?? ""}`.toLowerCase();
      return favorites.some(
        (item) => `${item.type}::${item.title}::${item.symbol ?? ""}`.toLowerCase() === key
      );
    },
    [favorites]
  );

  const createNotification = useCallback(
    (notification: Omit<NotificationItem, "id" | "timestamp" | "read">) => {
      const entry: NotificationItem = {
        ...notification,
        id: `notif-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: new Date().toISOString(),
        read: false,
      };

      setNotifications((current) => [entry, ...current].slice(0, 30));
      pushToast(notification.title, notification.severity === "high" ? "warning" : "info");
    },
    [pushToast]
  );

  const openGlobalSearch = useCallback(() => {
    setGlobalSearchOpen(true);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);
  }, []);

  const closeGlobalSearch = useCallback(() => {
    setGlobalSearchOpen(false);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);
  }, []);

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
    setGlobalSearchOpen(false);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);

    if (view === "filings") {
      createNotification({
        title: "Filings workspace opened",
        message: "Track new regulatory disclosures and key updates from one place.",
        category: "filing",
        severity: "low",
      });
    }

    if (view === "news") {
      createNotification({
        title: "News radar opened",
        message: "Sentiment and headline monitoring is now active for quick scanning.",
        category: "theme",
        severity: "low",
      });
    }

    if (view === "timeline") {
      createNotification({
        title: "Timeline feed opened",
        message: "Chronological event stream is ready for review.",
        category: "system",
        severity: "low",
      });
    }
  }, [createNotification]);

  const handleFavoriteSelect = useCallback(
    (favorite: FavoriteItem) => {
      if (favorite.type === "company") {
        setSearchSelection({
          stamp: Date.now(),
          discoveryQuery: favorite.symbol ?? favorite.title,
          filingsSymbol: favorite.symbol,
          newsSymbol: favorite.symbol,
        });
        goToView("discovery");
      } else if (favorite.type === "filing") {
        setSearchSelection({
          stamp: Date.now(),
          filingsSymbol: favorite.symbol,
          discoveryQuery: favorite.symbol,
        });
        goToView("filings");
      } else {
        setSearchSelection({
          stamp: Date.now(),
          newsSymbol: favorite.symbol,
        });
        goToView("news");
      }

      setFavoritesOpen(false);
      pushToast("Opened from favorites", "info");
    },
    [goToView, pushToast]
  );

  const toggleDashboardDensity = useCallback(() => {
    setDashboardPreferences((current) => ({
      ...current,
      density: current.density === "comfortable" ? "compact" : "comfortable",
    }));
  }, []);

  const toggleDashboardWidget = useCallback((widgetId: string) => {
    setDashboardPreferences((current) => {
      const hidden = new Set(current.hiddenWidgets);
      if (hidden.has(widgetId)) {
        hidden.delete(widgetId);
      } else {
        hidden.add(widgetId);
      }

      return {
        ...current,
        hiddenWidgets: Array.from(hidden),
      };
    });
  }, []);

  const resetDashboardPreferences = useCallback(() => {
    setDashboardPreferences({ density: "comfortable", hiddenWidgets: [] });
    pushToast("Dashboard layout reset", "success");
  }, [pushToast]);

  const createAlertRule = useCallback(() => {
    const normalizedSymbol = ruleSymbol.trim().toUpperCase();
    if (!ruleName.trim() || !normalizedSymbol) {
      pushToast("Rule name and symbol are required", "warning");
      return;
    }

    const thresholdValue = Number(ruleThreshold);
    const needsThreshold = ruleType !== "filing_event";
    const parsedThreshold = needsThreshold && Number.isFinite(thresholdValue) ? thresholdValue : undefined;

    const newRule: AlertRule = {
      id: `rule-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name: ruleName.trim(),
      type: ruleType,
      symbol: normalizedSymbol,
      threshold: parsedThreshold,
      enabled: true,
      createdAt: new Date().toISOString(),
    };

    setAlertRules((current) => [newRule, ...current].slice(0, 80));
    pushToast("Alert rule created", "success");
    setRuleName("");
  }, [pushToast, ruleName, ruleSymbol, ruleThreshold, ruleType]);

  const toggleAlertRule = useCallback((id: string) => {
    setAlertRules((current) =>
      current.map((rule) =>
        rule.id === id
          ? {
              ...rule,
              enabled: !rule.enabled,
              lastCheckedAt: new Date().toISOString(),
            }
          : rule
      )
    );
  }, []);

  const deleteAlertRule = useCallback(
    (id: string) => {
      setAlertRules((current) => current.filter((rule) => rule.id !== id));
      pushToast("Alert rule removed", "info");
    },
    [pushToast]
  );

  const runAlertRulesCheck = useCallback(() => {
    const now = new Date().toISOString();

    setAlertRules((current) => {
      const updated = current.map((rule) => {
        if (!rule.enabled) {
          return { ...rule, lastCheckedAt: now };
        }

        let triggered = false;

        if (rule.type === "filing_event") {
          triggered = TIMELINE_EVENTS.some(
            (event) =>
              event.company === rule.symbol &&
              event.type === "filing" &&
              new Date(event.timestamp).getTime() > Date.now() - 1000 * 60 * 60 * 36
          );
        }

        if (rule.type === "risk_beta_above") {
          const holdings = rule.symbol === "PORTFOLIO"
            ? PORTFOLIO_HOLDINGS
            : PORTFOLIO_HOLDINGS.filter((holding) => holding.symbol === rule.symbol);

          const threshold = rule.threshold ?? 1;
          triggered = holdings.some((holding) => holding.beta >= threshold);
        }

        if (rule.type === "theme_score_above") {
          const company = DISCOVERY_COMPANIES.find((item) => item.symbol === rule.symbol);
          const threshold = rule.threshold ?? 80;
          const maxThemeScore = company
            ? Math.max(...Object.values(company.themeScores))
            : 0;
          triggered = maxThemeScore >= threshold;
        }

        if (triggered) {
          createNotification({
            title: `Rule Triggered: ${rule.name}`,
            message: `${rule.symbol} matched ${rule.type.replace(/_/g, " ")} condition.`,
            category: rule.type === "filing_event" ? "filing" : rule.type === "risk_beta_above" ? "risk" : "theme",
            severity: "medium",
          });
        }

        return {
          ...rule,
          lastCheckedAt: now,
          lastTriggeredAt: triggered ? now : rule.lastTriggeredAt,
        };
      });

      return updated;
    });

    pushToast("Alert rules evaluated", "info");
  }, [createNotification, pushToast]);

  const globalSearchResults = useMemo<GlobalSearchResult[]>(() => {
    const query = globalSearchQuery.trim().toLowerCase();
    const results: GlobalSearchResult[] = [];

    if (!query) {
      results.push(
        {
          id: "hint-company",
          type: "company",
          title: "Search company symbols",
          subtitle: "Examples: RELIANCE, TCS, INFY",
          onSelect: () => {
            setSearchSelection({ stamp: Date.now(), discoveryQuery: "RELIANCE" });
            goToView("discovery");
          },
        },
        {
          id: "hint-theme",
          type: "theme",
          title: "Jump to themes",
          subtitle: "Examples: AI, Defense, Renewable",
          onSelect: () => {
            setSearchSelection({ stamp: Date.now(), discoveryTheme: "AI" });
            goToView("discovery");
          },
        },
        {
          id: "hint-query",
          type: "query",
          title: "Ask Iris quickly",
          subtitle: "Open chat with a prepared prompt",
          onSelect: () => {
            setSearchSelection({
              stamp: Date.now(),
              chatPrompt: "Summarize portfolio risk in simple language.",
            });
            goToView("chat");
          },
        }
      );
      return results;
    }

    for (const company of DISCOVERY_COMPANIES) {
      const searchable = `${company.symbol} ${company.name} ${company.sector}`.toLowerCase();
      if (!searchable.includes(query)) continue;

      results.push({
        id: `company-${company.symbol}`,
        type: "company",
        title: `${company.symbol} · ${company.name}`,
        subtitle: `Open filings and discovery for ${company.symbol}`,
        onSelect: () => {
          setSearchSelection({
            stamp: Date.now(),
            discoveryQuery: company.symbol,
            filingsSymbol: company.symbol,
            newsSymbol: company.symbol,
          });
          goToView("filings");
        },
      });
    }

    const themeSet = new Set<string>();
    for (const company of DISCOVERY_COMPANIES) {
      for (const theme of Object.keys(company.themeScores)) {
        if (theme.toLowerCase().includes(query)) {
          themeSet.add(theme);
        }
      }
    }

    for (const theme of themeSet) {
      results.push({
        id: `theme-${theme}`,
        type: "theme",
        title: `Theme: ${theme}`,
        subtitle: "Open Discovery with theme filter",
        onSelect: () => {
          setSearchSelection({ stamp: Date.now(), discoveryTheme: theme });
          goToView("discovery");
        },
      });
    }

    for (const event of TIMELINE_EVENTS) {
      const searchable = `${event.company} ${event.title} ${event.summary} ${event.sourceLabel}`.toLowerCase();
      if (!searchable.includes(query)) continue;

      results.push({
        id: `event-${event.id}`,
        type: "event",
        title: `${event.company} · ${event.title}`,
        subtitle: "Open in timeline details",
        onSelect: () => {
          setSearchSelection({
            stamp: Date.now(),
            timelineQuery: event.company,
            timelineEventId: event.id,
          });
          goToView("timeline");
        },
      });
    }

    for (const template of QUICK_QUERY_TEMPLATES) {
      if (!template.toLowerCase().includes(query)) continue;
      results.push({
        id: `query-${template}`,
        type: "query",
        title: template,
        subtitle: "Use as chat starter",
        onSelect: () => {
          setSearchSelection({ stamp: Date.now(), chatPrompt: template });
          goToView("chat");
        },
      });
    }

    return results.slice(0, 18);
  }, [globalSearchQuery, goToView]);

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
        id: "go-company",
        label: "Go to Company Workspace",
        hint: "Navigation",
        keywords: "company workspace symbol details",
        action: () => {
          setSearchSelection({ stamp: Date.now(), companySymbol: "RELIANCE" });
          goToView("company");
        },
      },
      {
        id: "go-company-from-context",
        label: "Open Company from Current Context",
        hint: "Navigation",
        keywords: "company current symbol context",
        action: () => {
          const symbol =
            searchSelection?.companySymbol ??
            searchSelection?.filingsSymbol ??
            searchSelection?.newsSymbol ??
            searchSelection?.discoveryQuery ??
            "RELIANCE";
          setSearchSelection({ stamp: Date.now(), companySymbol: symbol });
          goToView("company");
        },
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
      {
        id: "open-alert-rules",
        label: "Open Alert Rules Builder",
        hint: "Automation",
        keywords: "alert rules automation triggers notifications",
        action: () => {
          setAlertRulesOpen(true);
          closePalette();
        },
      },
      {
        id: "run-alert-check",
        label: "Run Alert Rules Check",
        hint: "Automation",
        keywords: "alert evaluate check now",
        action: () => {
          runAlertRulesCheck();
          closePalette();
        },
      },
      {
        id: "open-notifications",
        label: "Open Notifications",
        hint: "Inbox",
        keywords: "notifications alerts inbox bell",
        action: () => {
          setNotificationsOpen(true);
          closePalette();
        },
      },
      {
        id: "mark-all-read",
        label: "Mark All Notifications Read",
        hint: "Inbox",
        keywords: "notifications read clear alerts",
        action: () => {
          markAllNotificationsRead();
          closePalette();
        },
      },
    ],
    [
      closePalette,
      goToView,
      markAllNotificationsRead,
      runAlertRulesCheck,
      searchSelection?.companySymbol,
      searchSelection?.discoveryQuery,
      searchSelection?.filingsSymbol,
      searchSelection?.newsSymbol,
      theme,
      toggleTheme,
    ]
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
    if (!globalSearchOpen) return;
    window.requestAnimationFrame(() => {
      globalSearchInputRef.current?.focus();
    });
  }, [globalSearchOpen]);

  useEffect(() => {
    setPaletteActiveIndex(0);
  }, [paletteQuery]);

  useEffect(() => {
    setGlobalSearchIndex(0);
  }, [globalSearchQuery]);

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

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setGlobalSearchOpen((current) => {
          if (current) {
            setGlobalSearchQuery("");
            setGlobalSearchIndex(0);
            return false;
          }
          return true;
        });
        return;
      }

      if (globalSearchOpen) {
        if (event.key === "Escape") {
          event.preventDefault();
          closeGlobalSearch();
          return;
        }

        if (event.key === "ArrowDown") {
          event.preventDefault();
          setGlobalSearchIndex((current) =>
            globalSearchResults.length ? (current + 1) % globalSearchResults.length : 0
          );
          return;
        }

        if (event.key === "ArrowUp") {
          event.preventDefault();
          setGlobalSearchIndex((current) =>
            globalSearchResults.length
              ? (current - 1 + globalSearchResults.length) % globalSearchResults.length
              : 0
          );
          return;
        }

        if (event.key === "Enter") {
          event.preventDefault();
          const result = globalSearchResults[globalSearchIndex] ?? globalSearchResults[0];
          result?.onSelect();
        }
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
  }, [
    closeGlobalSearch,
    closePalette,
    filteredCommands,
    globalSearchIndex,
    globalSearchOpen,
    globalSearchResults,
    paletteActiveIndex,
    paletteOpen,
  ]);

  const page = useMemo(() => {
    switch (activeView) {
      case "dashboard":
        return (
          <DashboardView
            preferences={dashboardPreferences}
            onToggleDensity={toggleDashboardDensity}
            onToggleWidget={toggleDashboardWidget}
            onResetPreferences={resetDashboardPreferences}
          />
        );
      case "company":
        return (
          <CompanyWorkspaceView
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
          />
        );
      case "chat":
        return <ChatView searchSelection={searchSelection} />;
      case "discovery":
        return (
          <DiscoveryView
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "portfolio":
        return <PortfolioView />;
      case "filings":
        return (
          <FilingsView
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "timeline":
        return (
          <TimelineView
            searchSelection={searchSelection}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "news":
        return (
          <NewsView
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "settings":
        return (
          <SettingsView
            theme={theme}
            onToggleTheme={toggleTheme}
            favoritesCount={favorites.length}
            unreadNotifications={unreadCount}
          />
        );
      default:
        return (
          <DashboardView
            preferences={dashboardPreferences}
            onToggleDensity={toggleDashboardDensity}
            onToggleWidget={toggleDashboardWidget}
            onResetPreferences={resetDashboardPreferences}
          />
        );
    }
  }, [
    activeView,
    addFavorite,
    dashboardPreferences,
    favorites.length,
    goToView,
    isFavorited,
    resetDashboardPreferences,
    searchSelection,
    theme,
    toggleDashboardDensity,
    toggleDashboardWidget,
    toggleTheme,
    unreadCount,
  ]);

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

        <button
          type="button"
          className="notification-bell"
          onClick={() => setNotificationsOpen(true)}
          aria-label="Open notifications"
        >
          <span className="notification-bell-left">
            <Bell size={15} />
            Notifications
          </span>
          <span className={`notification-count ${unreadCount ? "has-unread" : ""}`}>
            {unreadCount}
          </span>
        </button>

        <button
          type="button"
          className="notification-bell"
          onClick={() => setAlertRulesOpen(true)}
          aria-label="Open alert rules"
        >
          <span className="notification-bell-left">
            <ShieldAlert size={15} />
            Alert Rules
          </span>
          <span className={`notification-count ${activeRulesCount ? "has-unread" : ""}`}>
            {activeRulesCount}
          </span>
        </button>

        <button
          type="button"
          className="favorites-bell"
          onClick={() => setFavoritesOpen(true)}
          aria-label="Open favorites"
        >
          <span className="notification-bell-left">
            <BookmarkCheck size={15} />
            Favorites
          </span>
          <span className="notification-count">{favorites.length}</span>
        </button>

        <button
          type="button"
          className="secondary-btn mini-btn favorites-clear-btn"
          onClick={() => {
            setFavorites([]);
            pushToast("Favorites cleared", "info");
          }}
        >
          Clear Favorites
        </button>

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

        <button type="button" className="global-search-shortcut" onClick={openGlobalSearch}>
          <span className="command-shortcut-left">
            <Search size={14} />
            Global Search
          </span>
          <span className="kbd-chip">Ctrl/Cmd + J</span>
        </button>

        <nav className="nav-stack">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => goToView(item.key)}
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

      {globalSearchOpen ? (
        <div className="global-search-overlay" role="dialog" aria-modal="true" aria-label="Global search">
          <button type="button" className="global-search-backdrop" onClick={closeGlobalSearch} />

          <div className="global-search-panel">
            <div className="global-search-head">
              <p className="results-title">Global Search</p>
              <span className="chip">Search company, theme, event, or query</span>
            </div>

            <div className="command-input-row">
              <Search size={15} />
              <input
                ref={globalSearchInputRef}
                value={globalSearchQuery}
                onChange={(event) => setGlobalSearchQuery(event.target.value)}
                placeholder="Try: RELIANCE, defense, AI, risk..."
              />
            </div>

            <div className="global-search-results">
              {globalSearchResults.length ? (
                globalSearchResults.map((result, index) => (
                  <button
                    type="button"
                    key={result.id}
                    className={`global-search-item ${index === globalSearchIndex ? "active" : ""}`}
                    onMouseEnter={() => setGlobalSearchIndex(index)}
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
      ) : null}

      {notificationsOpen ? (
        <div className="notification-overlay" role="dialog" aria-modal="true" aria-label="Notifications panel">
          <button
            type="button"
            className="notification-backdrop"
            onClick={() => setNotificationsOpen(false)}
          />

          <aside className="notification-panel">
            <div className="notification-panel-head">
              <div>
                <p className="results-title">Alerts Center</p>
                <h3>Notifications</h3>
              </div>
              <button
                type="button"
                className="notification-close"
                onClick={() => setNotificationsOpen(false)}
                aria-label="Close notifications panel"
              >
                <X size={16} />
              </button>
            </div>

            <div className="notification-panel-actions">
              <select
                className="type-select"
                value={notificationFilter}
                onChange={(event) =>
                  setNotificationFilter(event.target.value as "all" | NotificationCategory)
                }
              >
                <option value="all">All categories</option>
                <option value="filing">Filing</option>
                <option value="risk">Risk</option>
                <option value="theme">Theme</option>
                <option value="system">System</option>
              </select>

              <button type="button" className="secondary-btn mini-btn" onClick={markAllNotificationsRead}>
                <CheckCheck size={14} />
                Mark all read
              </button>
            </div>

            <div className="notification-list">
              {filteredNotifications.length ? (
                filteredNotifications.map((notification) => (
                  <article
                    key={notification.id}
                    className={`notification-item ${notification.read ? "read" : "unread"}`}
                  >
                    <div className="notification-item-head">
                      <span className={`chip notif-${notification.category}`}>{notification.category}</span>
                      <span className={`chip notif-severity-${notification.severity}`}>
                        {notification.severity}
                      </span>
                    </div>

                    <h4>{notification.title}</h4>
                    <p>{notification.message}</p>
                    <small>{new Date(notification.timestamp).toLocaleString()}</small>

                    <div className="notification-item-actions">
                      {!notification.read ? (
                        <button
                          type="button"
                          className="secondary-btn mini-btn"
                          onClick={() => markNotificationRead(notification.id)}
                        >
                          Mark read
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="secondary-btn mini-btn"
                        onClick={() => dismissNotification(notification.id)}
                      >
                        Dismiss
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div className="list-item single-line">
                  <p>No notifications in this category.</p>
                </div>
              )}
            </div>
          </aside>
        </div>
      ) : null}

      {favoritesOpen ? (
        <div className="favorites-overlay" role="dialog" aria-modal="true" aria-label="Favorites panel">
          <button
            type="button"
            className="favorites-backdrop"
            onClick={() => setFavoritesOpen(false)}
          />

          <aside className="favorites-panel">
            <div className="notification-panel-head">
              <div>
                <p className="results-title">Saved Items</p>
                <h3>Favorites</h3>
              </div>
              <button
                type="button"
                className="notification-close"
                onClick={() => setFavoritesOpen(false)}
                aria-label="Close favorites panel"
              >
                <X size={16} />
              </button>
            </div>

            <div className="notification-panel-actions">
              <select
                className="type-select"
                value={favoriteFilter}
                onChange={(event) => setFavoriteFilter(event.target.value as "all" | FavoriteType)}
              >
                <option value="all">All favorites</option>
                <option value="company">Company</option>
                <option value="filing">Filing</option>
                <option value="headline">Headline</option>
              </select>
            </div>

            <div className="notification-list">
              {filteredFavorites.length ? (
                filteredFavorites.map((favorite) => (
                  <article key={favorite.id} className="notification-item unread">
                    <div className="notification-item-head">
                      <span className={`chip favorite-${favorite.type}`}>{favorite.type}</span>
                      <span className="chip">{new Date(favorite.createdAt).toLocaleDateString()}</span>
                    </div>

                    <h4>{favorite.title}</h4>
                    {favorite.subtitle ? <p>{favorite.subtitle}</p> : null}
                    {favorite.symbol ? <small>Symbol: {favorite.symbol}</small> : null}

                    <div className="notification-item-actions">
                      <button
                        type="button"
                        className="secondary-btn mini-btn"
                        onClick={() => handleFavoriteSelect(favorite)}
                      >
                        Open
                      </button>
                      <button
                        type="button"
                        className="secondary-btn mini-btn"
                        onClick={() => removeFavorite(favorite.id)}
                      >
                        <Trash2 size={13} />
                        Remove
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div className="list-item single-line">
                  <p>No favorites saved yet.</p>
                </div>
              )}
            </div>
          </aside>
        </div>
      ) : null}

      {alertRulesOpen ? (
        <div className="favorites-overlay" role="dialog" aria-modal="true" aria-label="Alert rules panel">
          <button
            type="button"
            className="favorites-backdrop"
            onClick={() => setAlertRulesOpen(false)}
          />

          <aside className="favorites-panel">
            <div className="notification-panel-head">
              <div>
                <p className="results-title">Automation</p>
                <h3>Alert Rules Builder</h3>
              </div>
              <button
                type="button"
                className="notification-close"
                onClick={() => setAlertRulesOpen(false)}
                aria-label="Close alert rules panel"
              >
                <X size={16} />
              </button>
            </div>

            <div className="rule-builder-form">
              <input
                className="rule-input"
                placeholder="Rule name"
                value={ruleName}
                onChange={(event) => setRuleName(event.target.value)}
              />

              <select
                className="type-select"
                value={ruleType}
                onChange={(event) => setRuleType(event.target.value as AlertRuleType)}
              >
                <option value="filing_event">Filing Event</option>
                <option value="risk_beta_above">Risk: Beta Above</option>
                <option value="theme_score_above">Theme Score Above</option>
              </select>

              <input
                className="rule-input"
                placeholder="Symbol (e.g. RELIANCE or PORTFOLIO)"
                value={ruleSymbol}
                onChange={(event) => setRuleSymbol(event.target.value)}
              />

              {ruleType !== "filing_event" ? (
                <input
                  className="rule-input"
                  placeholder="Threshold"
                  value={ruleThreshold}
                  onChange={(event) => setRuleThreshold(event.target.value)}
                />
              ) : null}

              <div className="rule-actions">
                <button type="button" className="primary-btn" onClick={createAlertRule}>
                  Add Rule
                </button>
                <button type="button" className="secondary-btn mini-btn" onClick={runAlertRulesCheck}>
                  Run Check
                </button>
              </div>
            </div>

            <div className="notification-list">
              {alertRules.length ? (
                alertRules.map((rule) => (
                  <article key={rule.id} className={`notification-item ${rule.enabled ? "unread" : "read"}`}>
                    <div className="notification-item-head">
                      <span className="chip notif-system">{rule.type.replace(/_/g, " ")}</span>
                      <span className={`chip ${rule.enabled ? "positive" : ""}`}>
                        {rule.enabled ? "enabled" : "disabled"}
                      </span>
                    </div>

                    <h4>{rule.name}</h4>
                    <p>
                      Symbol: {rule.symbol}
                      {rule.threshold !== undefined ? ` · threshold ${rule.threshold}` : ""}
                    </p>
                    <small>
                      {rule.lastTriggeredAt
                        ? `Last triggered: ${new Date(rule.lastTriggeredAt).toLocaleString()}`
                        : "Not triggered yet"}
                    </small>

                    <div className="notification-item-actions">
                      <button
                        type="button"
                        className="secondary-btn mini-btn"
                        onClick={() => toggleAlertRule(rule.id)}
                      >
                        {rule.enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        type="button"
                        className="secondary-btn mini-btn"
                        onClick={() => deleteAlertRule(rule.id)}
                      >
                        <Trash2 size={13} />
                        Delete
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div className="list-item single-line">
                  <p>No alert rules created yet.</p>
                </div>
              )}
            </div>
          </aside>
        </div>
      ) : null}

      {toasts.length ? (
        <div className="toast-stack" aria-live="polite" aria-atomic="false">
          {toasts.map((toast) => (
            <div key={toast.id} className={`toast-item toast-${toast.tone}`}>
              <p>{toast.message}</p>
              <button
                type="button"
                className="toast-close"
                onClick={() => removeToast(toast.id)}
                aria-label="Dismiss toast"
              >
                <X size={14} />
              </button>
            </div>
          ))}
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

function DashboardView(props: {
  preferences: DashboardPreferences;
  onToggleDensity: () => void;
  onToggleWidget: (widgetId: string) => void;
  onResetPreferences: () => void;
}) {
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

  const isWidgetVisible = useCallback(
    (id: string) => !props.preferences.hiddenWidgets.includes(id),
    [props.preferences.hiddenWidgets]
  );

  const cardDensityClass = props.preferences.density === "compact" ? "card-compact" : "";

  const headlineCount = headlines.results?.length ?? headlines.totalResults ?? 0;
  const latestHeadline = headlines.results?.[0]?.title ?? "No headlines yet";

  return (
    <section className="page-wrap">
      <PageHeader
        title="Market Command Center"
        subtitle="Track activity, spot risks, and jump into analysis flows quickly."
        right={
          <div className="dashboard-actions">
            <button type="button" className="secondary-btn mini-btn" onClick={props.onToggleDensity}>
              Density: {props.preferences.density}
            </button>
            <button type="button" className="secondary-btn mini-btn" onClick={props.onResetPreferences}>
              Reset Layout
            </button>
            <button type="button" className="primary-btn" onClick={() => void loadDashboardData()}>
              {loading ? "Refreshing..." : "Refresh Data"}
            </button>
          </div>
        }
      />

      <div className="dashboard-widget-toggles">
        {DASHBOARD_WIDGETS.map((widget) => (
          <button
            key={widget.id}
            type="button"
            className={`widget-toggle-chip ${isWidgetVisible(widget.id) ? "active" : ""}`}
            onClick={() => props.onToggleWidget(widget.id)}
          >
            {widget.label}
          </button>
        ))}
      </div>

      {error ? <div className="notice warning">{error}</div> : null}

      <div className="kpi-grid">
        {isWidgetVisible("kpi-portfolio") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Portfolio Companies</p>
            <h2>{loading ? "--" : holdingsCount}</h2>
            <small>From Upstox holdings</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-headlines") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Live Headlines</p>
            <h2>{loading ? "--" : headlineCount}</h2>
            <small>From NewsData market feed</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-health") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>Backend Health</p>
            <h2>{loading ? "--" : (health.status ?? "unknown")}</h2>
            <small>{health.message ?? "No status message"}</small>
          </article>
        ) : null}

        {isWidgetVisible("kpi-api") ? (
          <article className={`kpi-card ${cardDensityClass}`}>
            <p>API Version</p>
            <h2>{loading ? "--" : (apiStatus.api_version ?? "n/a")}</h2>
            <small>Status: {apiStatus.status ?? "unknown"}</small>
          </article>
        ) : null}
      </div>

      <div className="split-grid">
        {isWidgetVisible("feature-concentration") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>Portfolio Concentration</h3>
            </div>
            <p>
              Top 3 positions account for 47% of capital. Consider rebalancing to reduce concentration risk.
            </p>
          </article>
        ) : null}

        {isWidgetVisible("feature-headline") ? (
          <article className={`feature-card ${cardDensityClass}`}>
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Latest Market Headline</h3>
            </div>
            <p>{loading ? "Loading latest headline..." : latestHeadline}</p>
          </article>
        ) : null}
      </div>
    </section>
  );
}

function ChatView(props: { searchSelection: SearchSelection | null }) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [explanationMode, setExplanationMode] = useState<ExplanationMode>("analyst");
  const [showSources, setShowSources] = useState(true);
  const [composerText, setComposerText] = useState("");

  const suggestions = [
    "What changed in RELIANCE latest filing?",
    "Summarize risk signals for my portfolio in simple terms.",
    "Compare IT services sentiment: TCS vs INFY.",
    "Explain why defense theme is heating up this week.",
  ];

  const chatMessages: ChatMessage[] =
    explanationMode === "simple"
      ? [
          {
            id: "assistant-simple-1",
            role: "assistant",
            text: "I checked your watchlist and saw one key thing: your top stocks are still strong, but one banking stock is slowing a bit. Nothing panic-worthy yet, just keep watching next updates.",
            sources: [
              "Timeline Feed · Risk monitor signal",
              "Filings Tracker · Latest disclosures",
            ],
          },
          {
            id: "user-simple-1",
            role: "user",
            text: "Can you explain in plain language what I should do this week?",
          },
          {
            id: "assistant-simple-2",
            role: "assistant",
            text: "Sure. Keep your portfolio mostly as-is, read two new filings (RELIANCE and TATAPOWER), and avoid big changes until the next bank update comes in.",
            sources: [
              "Notifications · Filing alerts",
              "Discovery Engine · Theme score snapshots",
            ],
          },
        ]
      : [
          {
            id: "assistant-analyst-1",
            role: "assistant",
            text: "Portfolio risk posture remains moderate. Concentration in top holdings is elevated, but near-term narrative quality remains constructive due to stable filing commentary and improving sector momentum in defense and renewables.",
            sources: [
              "Dashboard · Portfolio concentration card",
              "Timeline Feed · Sector event flow",
            ],
          },
          {
            id: "user-analyst-1",
            role: "user",
            text: "Summarize major risk signals for my top holdings this week.",
          },
          {
            id: "assistant-analyst-2",
            role: "assistant",
            text: "Primary watchpoints: (1) moderation signal in banking credit momentum, (2) valuation sensitivity in high-theme momentum names, and (3) execution dependency on capex-to-margin conversion for conglomerate and utility exposures.",
            sources: [
              "Notifications · Risk monitor",
              "News & Sentiment · Narrative drift",
              "Filings Tracker · Quarterly disclosures",
            ],
          },
        ];

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.chatPrompt) {
      setComposerText(props.searchSelection.chatPrompt);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  return (
    <section className="page-wrap">
      <PageHeader
        title="Iris Research Copilot"
        subtitle="Ask focused questions across filings, portfolio, and market sentiment."
        right={
          <div className="chat-controls">
            <button
              type="button"
              className={`mode-pill ${explanationMode === "analyst" ? "active" : ""}`}
              onClick={() => setExplanationMode("analyst")}
            >
              <BookOpenText size={14} />
              Analyst Mode
            </button>
            <button
              type="button"
              className={`mode-pill ${explanationMode === "simple" ? "active" : ""}`}
              onClick={() => setExplanationMode("simple")}
            >
              <WandSparkles size={14} />
              Explain Simply
            </button>
            <button
              type="button"
              className={`mode-pill ${showSources ? "active" : ""}`}
              onClick={() => setShowSources((current) => !current)}
            >
              Sources {showSources ? "On" : "Off"}
            </button>
          </div>
        }
      />

      <div className="chat-suggestions">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="chat-suggestion-chip"
            onClick={() => setComposerText(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>

      <article className="chat-shell">
        <div className="chat-messages">
          {chatMessages.map((message) => (
            <div key={message.id} className={`message ${message.role}`}>
              <p>{message.text}</p>
              {showSources && message.role === "assistant" && message.sources?.length ? (
                <div className="source-list">
                  {message.sources.map((source) => (
                    <span key={`${message.id}-${source}`} className="source-chip">
                      {source}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>

        <div className="chat-input-row">
          <input
            placeholder="Ask Iris anything about equities..."
            value={composerText}
            onChange={(event) => setComposerText(event.target.value)}
          />
          <button type="button" className="primary-btn">Send</button>
        </div>
      </article>
    </section>
  );
}

function CompanyWorkspaceView(props: {
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [symbolInput, setSymbolInput] = useState("RELIANCE");
  const [activeSymbol, setActiveSymbol] = useState("RELIANCE");
  const [activeTab, setActiveTab] = useState<"overview" | "filings" | "sentiment" | "timeline" | "chat">(
    "overview"
  );
  const [reportTitle, setReportTitle] = useState("");
  const [reportSections, setReportSections] = useState<ReportSectionId[]>([
    "summary",
    "risks",
    "financials",
    "themes",
  ]);
  const [reportAudience, setReportAudience] = useState<"retail" | "analyst">("analyst");
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    const symbol =
      props.searchSelection.companySymbol ??
      props.searchSelection.filingsSymbol ??
      props.searchSelection.newsSymbol ??
      props.searchSelection.discoveryQuery;

    if (symbol) {
      const normalized = symbol.toUpperCase();
      setActiveSymbol(normalized);
      setSymbolInput(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

  const companyData = useMemo(() => {
    const found = DISCOVERY_COMPANIES.find((company) => company.symbol === activeSymbol);
    if (found) return found;

    return {
      symbol: activeSymbol,
      name: `${activeSymbol} Corp`,
      sector: "Unknown",
      marketCapBn: 0,
      insight: "No local company profile found yet. Add this symbol to discovery dataset.",
      themeScores: {},
    } as DiscoveryCompany;
  }, [activeSymbol]);

  const companyTimeline = useMemo(
    () => TIMELINE_EVENTS.filter((event) => event.company === activeSymbol).slice(0, 6),
    [activeSymbol]
  );

  const topThemes = useMemo(
    () => Object.entries(companyData.themeScores).sort((a, b) => b[1] - a[1]).slice(0, 5),
    [companyData.themeScores]
  );

  const profileTitle = `${companyData.symbol} · ${companyData.name}`;

  const generatedReport = useMemo(() => {
    if (!reportGeneratedAt) return null;

    const topTheme = topThemes[0]?.[0] ?? "No clear dominant theme";
    const topThemeScore = topThemes[0]?.[1] ?? 0;

    const sections: string[] = [];

    if (reportSections.includes("summary")) {
      sections.push(
        `Executive Summary:\n${companyData.name} (${companyData.symbol}) currently shows strongest narrative strength in ${topTheme} with theme score ${topThemeScore}/100. Sector context remains ${companyData.sector}.`
      );
    }

    if (reportSections.includes("risks")) {
      sections.push(
        `Key Risks:\n1) Execution risk around near-term filings guidance.\n2) Valuation sensitivity if sector momentum cools.\n3) Sentiment volatility around macro updates.`
      );
    }

    if (reportSections.includes("financials")) {
      sections.push(
        `Financial Snapshot:\nMarket Cap: $${companyData.marketCapBn.toFixed(1)}B\nRecent timeline events: ${companyTimeline.length}\nPrimary sector: ${companyData.sector}`
      );
    }

    if (reportSections.includes("themes")) {
      const themeText = topThemes.length
        ? topThemes.map(([theme, score]) => `${theme} (${score})`).join(", ")
        : "No theme signal available";

      sections.push(`Theme Outlook:\nDominant theme signals: ${themeText}.`);
    }

    const audienceText =
      reportAudience === "retail"
        ? "Retail framing: keep explanations concise and action oriented."
        : "Analyst framing: include context, assumptions, and scenario sensitivity.";

    return {
      title: reportTitle.trim() || `${companyData.symbol} Research Brief`,
      generatedAt: reportGeneratedAt,
      audienceText,
      body: sections.join("\n\n"),
    };
  }, [
    companyData.marketCapBn,
    companyData.name,
    companyData.sector,
    companyData.symbol,
    companyTimeline.length,
    reportAudience,
    reportGeneratedAt,
    reportSections,
    reportTitle,
    topThemes,
  ]);

  const toggleReportSection = (sectionId: ReportSectionId) => {
    setReportSections((current) => {
      if (current.includes(sectionId)) {
        const next = current.filter((id) => id !== sectionId);
        return next.length ? next : current;
      }
      return [...current, sectionId];
    });
  };

  const triggerReportGeneration = () => {
    setReportGeneratedAt(new Date().toISOString());
  };

  const exportReportAsText = () => {
    if (!generatedReport) return;

    const payload = [
      generatedReport.title,
      `Generated: ${new Date(generatedReport.generatedAt).toLocaleString()}`,
      generatedReport.audienceText,
      "",
      generatedReport.body,
    ].join("\n");

    const blob = new Blob([payload], { type: "text/plain;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${companyData.symbol.toLowerCase()}-report.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Company Workspace"
        subtitle="One research cockpit per company: filings, sentiment, timeline, and company-context chat."
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
              placeholder="Enter company symbol"
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value)}
            />
          </form>
        }
      />

      <div className="company-header-card">
        <div className="company-header-main">
          <p className="discovery-symbol">{companyData.symbol}</p>
          <h2>{companyData.name}</h2>
          <p>{companyData.insight}</p>
          <div className="chip-row">
            <span className="chip">Sector: {companyData.sector}</span>
            <span className="chip">Market Cap: ${companyData.marketCapBn.toFixed(1)}B</span>
          </div>
        </div>
        <div className="company-header-actions">
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() =>
              props.addFavorite({
                type: "company",
                symbol: companyData.symbol,
                title: profileTitle,
                subtitle: companyData.insight,
              })
            }
          >
            {props.isFavorited({ type: "company", symbol: companyData.symbol, title: profileTitle }) ? (
              <>
                <BookmarkCheck size={14} />
                Saved
              </>
            ) : (
              <>
                <Bookmark size={14} />
                Save Company
              </>
            )}
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => {
              setActiveTab("chat");
            }}
          >
            <ArrowUpRight size={14} />
            Ask Iris
          </button>
        </div>
      </div>

      <div className="company-tabs">
        {[
          ["overview", "Overview"],
          ["filings", "Filings"],
          ["sentiment", "Sentiment"],
          ["timeline", "Timeline"],
          ["chat", "Chat"],
        ].map(([tabId, label]) => (
          <button
            key={tabId}
            type="button"
            className={`company-tab-btn ${activeTab === tabId ? "active" : ""}`}
            onClick={() => setActiveTab(tabId as typeof activeTab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" ? (
        <div className="split-grid">
          <article className="feature-card">
            <div className="feature-head">
              <Compass size={18} />
              <h3>Theme Exposure</h3>
            </div>
            {topThemes.length ? (
              <div className="chip-row">
                {topThemes.map(([theme, score]) => (
                  <span key={`${companyData.symbol}-${theme}`} className="chip discovery-theme-chip">
                    {theme} · {score}
                  </span>
                ))}
              </div>
            ) : (
              <p>No theme scores found for this symbol in local discovery set.</p>
            )}
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <Clock3 size={18} />
              <h3>Recent Timeline Count</h3>
            </div>
            <p>{companyTimeline.length} recent events found for this company.</p>
          </article>
        </div>
      ) : null}

      {activeTab === "filings" ? (
        <article className="feature-card">
          <div className="feature-head">
            <FileText size={18} />
            <h3>Filings Snapshot ({companyData.symbol})</h3>
          </div>
          <p>
            Open the full Filings page for deep drill-down. This workspace keeps the symbol context
            pinned for quick navigation.
          </p>
        </article>
      ) : null}

      {activeTab === "sentiment" ? (
        <article className="feature-card">
          <div className="feature-head">
            <TrendingUp size={18} />
            <h3>Sentiment Snapshot ({companyData.symbol})</h3>
          </div>
          <p>
            Use this tab as a context anchor, then jump to News for live headlines and sentiment feed
            scoped to {companyData.symbol}.
          </p>
        </article>
      ) : null}

      {activeTab === "timeline" ? (
        <article className="list-card">
          {companyTimeline.length ? (
            companyTimeline.map((event) => (
              <div key={event.id} className="list-item">
                <p>{event.title}</p>
                <span>{new Date(event.timestamp).toLocaleString()}</span>
              </div>
            ))
          ) : (
            <div className="list-item single-line">
              <p>No timeline events for {companyData.symbol} in local dataset.</p>
            </div>
          )}
        </article>
      ) : null}

      {activeTab === "chat" ? (
        <article className="chat-shell">
          <div className="chat-messages">
            <div className="message assistant">
              <p>
                You are now in {companyData.symbol} context. Ask company-specific questions to get
                tighter research answers.
              </p>
              <div className="source-list">
                <span className="source-chip">Company Workspace · Context mode</span>
              </div>
            </div>
          </div>
          <div className="chat-input-row">
            <input
              value={`What are the key risks and opportunities for ${companyData.symbol} this quarter?`}
              readOnly
            />
            <button type="button" className="primary-btn">Send</button>
          </div>
        </article>
      ) : null}

      <article className="report-builder-card">
        <div className="feature-head">
          <FileText size={18} />
          <h3>Report Generation Workspace</h3>
        </div>

        <div className="report-builder-grid">
          <label className="report-field">
            <span>Report title</span>
            <input
              value={reportTitle}
              onChange={(event) => setReportTitle(event.target.value)}
              placeholder={`${companyData.symbol} quarterly research brief`}
            />
          </label>

          <label className="report-field">
            <span>Audience</span>
            <select
              className="type-select"
              value={reportAudience}
              onChange={(event) => setReportAudience(event.target.value as "retail" | "analyst")}
            >
              <option value="analyst">Analyst</option>
              <option value="retail">Retail</option>
            </select>
          </label>
        </div>

        <div className="chip-row report-section-chips">
          {REPORT_SECTION_OPTIONS.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`widget-toggle-chip ${reportSections.includes(section.id) ? "active" : ""}`}
              onClick={() => toggleReportSection(section.id)}
            >
              {section.label}
            </button>
          ))}
        </div>

        <div className="report-action-row">
          <button type="button" className="primary-btn" onClick={triggerReportGeneration}>
            Generate Report
          </button>
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={exportReportAsText}
            disabled={!generatedReport}
          >
            Download .txt
          </button>
        </div>

        {generatedReport ? (
          <div className="report-preview">
            <h4>{generatedReport.title}</h4>
            <p>{generatedReport.audienceText}</p>
            <small>Generated: {new Date(generatedReport.generatedAt).toLocaleString()}</small>
            <pre>{generatedReport.body}</pre>
          </div>
        ) : (
          <p className="report-placeholder">
            Select sections and click Generate Report to build a company-specific brief.
          </p>
        )}
      </article>
    </section>
  );
}

function DiscoveryView(props: {
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [query, setQuery] = useState("");
  const [activeTheme, setActiveTheme] = useState<string>("all");
  const [activeSector, setActiveSector] = useState<string>("all");
  const [marketCapBucket, setMarketCapBucket] = useState<MarketCapBucket>("all");
  const [minThemeScore, setMinThemeScore] = useState<number>(60);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.discoveryQuery) {
      setQuery(props.searchSelection.discoveryQuery);
    }

    if (props.searchSelection.discoveryTheme) {
      setActiveTheme(props.searchSelection.discoveryTheme);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

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
                  <div className="discovery-card-actions">
                    <span className="chip">${company.marketCapBn.toFixed(1)}B</span>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      aria-label={`Save ${company.symbol} to favorites`}
                      onClick={() =>
                        props.addFavorite({
                          type: "company",
                          symbol: company.symbol,
                          title: `${company.symbol} · ${company.name}`,
                          subtitle: company.insight,
                        })
                      }
                    >
                      {props.isFavorited({
                        type: "company",
                        title: `${company.symbol} · ${company.name}`,
                        symbol: company.symbol,
                      }) ? (
                        <BookmarkCheck size={14} />
                      ) : (
                        <Bookmark size={14} />
                      )}
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      aria-label={`Open ${company.symbol} company workspace`}
                      onClick={() => {
                        props.setSearchSelection({
                          stamp: Date.now(),
                          companySymbol: company.symbol,
                        });
                        props.goToView("company");
                      }}
                    >
                      <ArrowUpRight size={14} />
                    </button>
                  </div>
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

                <button
                  type="button"
                  className="secondary-btn mini-btn open-company-btn"
                  onClick={() => {
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: company.symbol,
                    });
                    props.goToView("company");
                  }}
                >
                  Open Company
                </button>
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
  const totalWeight = useMemo(
    () => PORTFOLIO_HOLDINGS.reduce((acc, holding) => acc + holding.weight, 0),
    []
  );

  const weightedReturn = useMemo(
    () =>
      PORTFOLIO_HOLDINGS.reduce((acc, holding) => acc + (holding.returnPct * holding.weight) / 100, 0),
    []
  );

  const portfolioBeta = useMemo(
    () =>
      PORTFOLIO_HOLDINGS.reduce((acc, holding) => acc + (holding.beta * holding.weight) / totalWeight, 0),
    [totalWeight]
  );

  const portfolioVolatility = useMemo(
    () =>
      PORTFOLIO_HOLDINGS.reduce(
        (acc, holding) => acc + (holding.volatility * holding.weight) / totalWeight,
        0
      ),
    [totalWeight]
  );

  const riskFreeRate = 6.4;
  const benchmarkReturn = 1.1;
  const sharpeRatio = useMemo(
    () => ((weightedReturn - riskFreeRate / 12) / Math.max(portfolioVolatility / 10, 0.01)).toFixed(2),
    [portfolioVolatility, weightedReturn]
  );

  const benchmarkRelative = weightedReturn - benchmarkReturn;

  const sectorWeights = useMemo(() => {
    const map = new Map<string, number>();
    for (const holding of PORTFOLIO_HOLDINGS) {
      map.set(holding.sector, (map.get(holding.sector) ?? 0) + holding.weight);
    }
    return Array.from(map.entries())
      .map(([sector, weight]) => ({ sector, weight }))
      .sort((a, b) => b.weight - a.weight);
  }, []);

  const riskAlerts = useMemo(() => {
    return PORTFOLIO_HOLDINGS.filter((holding) => holding.beta > 1.15 || holding.volatility > 22);
  }, []);

  const maxSectorWeight = sectorWeights[0]?.weight ?? 1;

  return (
    <section className="page-wrap">
      <PageHeader
        title="Portfolio Intelligence"
        subtitle="Exposure, risk concentration, and opportunity signals at a glance."
      />

      <div className="kpi-grid portfolio-kpi-grid">
        <article className="kpi-card">
          <p>Portfolio Return (MTD)</p>
          <h2 className={weightedReturn >= 0 ? "positive" : "negative"}>{weightedReturn.toFixed(2)}%</h2>
          <small>Weighted by current allocation</small>
        </article>
        <article className="kpi-card">
          <p>Portfolio Beta</p>
          <h2>{portfolioBeta.toFixed(2)}</h2>
          <small>Benchmark beta reference = 1.00</small>
        </article>
        <article className="kpi-card">
          <p>Sharpe Ratio (Proxy)</p>
          <h2>{sharpeRatio}</h2>
          <small>Risk-free rate assumed at {riskFreeRate}%</small>
        </article>
        <article className="kpi-card">
          <p>Vs Nifty Benchmark</p>
          <h2 className={benchmarkRelative >= 0 ? "positive" : "negative"}>
            {benchmarkRelative >= 0 ? "+" : ""}
            {benchmarkRelative.toFixed(2)}%
          </h2>
          <small>Nifty assumed return {benchmarkReturn.toFixed(2)}%</small>
        </article>
      </div>

      <div className="split-grid portfolio-grid-extended">
        <article className="feature-card">
          <div className="feature-head">
            <BarChart3 size={18} />
            <h3>Sector Allocation</h3>
          </div>
          <div className="allocation-list">
            {sectorWeights.map((sectorItem) => (
              <div key={sectorItem.sector} className="allocation-item">
                <div className="allocation-meta">
                  <span>{sectorItem.sector}</span>
                  <span>{sectorItem.weight.toFixed(1)}%</span>
                </div>
                <div className="allocation-track">
                  <span
                    className="allocation-fill"
                    style={{ width: `${(sectorItem.weight / maxSectorWeight) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="feature-card">
          <div className="feature-head">
            <ShieldAlert size={18} />
            <h3>Risk Watchlist</h3>
          </div>
          {riskAlerts.length ? (
            <div className="risk-list">
              {riskAlerts.map((holding) => (
                <div key={holding.symbol} className="risk-item">
                  <p>{holding.symbol}</p>
                  <span>
                    Beta {holding.beta.toFixed(2)} · Vol {holding.volatility.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p>No elevated risk flags in current holdings.</p>
          )}
        </article>
      </div>

      <div className="table-card">
        <div className="table-head">
          <h3>Top Holdings</h3>
          <span>Analytics view</span>
        </div>

        {PORTFOLIO_HOLDINGS.map((holding) => (
          <div key={holding.symbol} className="table-row portfolio-row">
            <span>
              {holding.symbol}
              <small>{holding.company}</small>
            </span>
            <span>{holding.weight.toFixed(1)}%</span>
            <span className={holding.returnPct >= 0 ? "positive" : "negative"}>
              {holding.returnPct >= 0 ? "+" : ""}
              {holding.returnPct.toFixed(1)}%
            </span>
          </div>
        ))}
      </div>

      <div className="table-card">
        <div className="table-head">
          <h3>Valuation & Risk Factors</h3>
          <span>PE / PB / Volatility</span>
        </div>

        {PORTFOLIO_HOLDINGS.map((holding) => (
          <div key={`${holding.symbol}-factors`} className="table-row factor-row">
            <span>{holding.symbol}</span>
            <span>PE {holding.pe.toFixed(1)} | PB {holding.pb.toFixed(1)}</span>
            <span>Vol {holding.volatility.toFixed(1)}%</span>
          </div>
        ))}
      </div>

      <article className="feature-card benchmark-note">
        <div className="feature-head">
          <Flame size={18} />
          <h3>Benchmark Context</h3>
        </div>
        <p>
          Portfolio is currently {benchmarkRelative >= 0 ? "outperforming" : "underperforming"} the
          benchmark by {Math.abs(benchmarkRelative).toFixed(2)}%. Highest concentration risk remains in
          {" "}
          {sectorWeights[0]?.sector ?? "top sector"} with {sectorWeights[0]?.weight.toFixed(1) ?? "0"}%
          allocation.
        </p>
      </article>
    </section>
  );
}

function TimelineView(props: {
  searchSelection: SearchSelection | null;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | TimelineEvent["type"]>("all");
  const [impactFilter, setImpactFilter] = useState<"all" | TimelineEvent["impact"]>("all");
  const [selectedEventId, setSelectedEventId] = useState<string>(TIMELINE_EVENTS[0]?.id ?? "");

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.timelineQuery) {
      setQuery(props.searchSelection.timelineQuery);
    }

    if (props.searchSelection.timelineEventId) {
      setSelectedEventId(props.searchSelection.timelineEventId);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

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
                <span
                  className="timeline-open-company"
                  onClick={(e) => {
                    e.stopPropagation();
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: event.company,
                      timelineEventId: event.id,
                    });
                    props.goToView("company");
                  }}
                >
                  Open Company
                </span>
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

function FilingsView(props: {
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
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

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.filingsSymbol) {
      const normalized = props.searchSelection.filingsSymbol.toUpperCase();
      setActiveSymbol(normalized);
      setSymbolInput(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

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
                <div className="filing-content-wrap">
                  <p>
                    {(filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`)}
                  </p>
                  <span>{formatFilingDate(filing.filingDate ?? filing.acceptedDate)}</span>
                </div>
                <button
                  type="button"
                  className="favorite-icon-btn"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    props.addFavorite({
                      type: "filing",
                      symbol: activeSymbol,
                      title: (filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`),
                      subtitle: formatFilingDate(filing.filingDate ?? filing.acceptedDate),
                      url: filing.finalLink ?? filing.url,
                    });
                  }}
                  aria-label="Save filing to favorites"
                >
                  {props.isFavorited({
                    type: "filing",
                    symbol: activeSymbol,
                    title: (filing.type ?? "Filing") + " · " + (filing.title ?? `${activeSymbol} filing`),
                  }) ? (
                    <BookmarkCheck size={14} />
                  ) : (
                    <Bookmark size={14} />
                  )}
                </button>
                <button
                  type="button"
                  className="favorite-icon-btn"
                  onClick={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    props.setSearchSelection({
                      stamp: Date.now(),
                      companySymbol: activeSymbol,
                      filingsSymbol: activeSymbol,
                    });
                    props.goToView("company");
                  }}
                  aria-label="Open company workspace"
                >
                  <ArrowUpRight size={14} />
                </button>
              </a>
            ))
          : null}
      </div>
    </section>
  );
}

function NewsView(props: {
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
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

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.newsSymbol) {
      const normalized = props.searchSelection.newsSymbol.toUpperCase();
      setSymbolInput(normalized);
      setActiveSymbol(normalized);
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [lastSelectionStamp, props.searchSelection]);

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
                <div key={`${article.article_id ?? article.link ?? index}`} className="feed-item-wrap">
                  <a
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
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() =>
                      props.addFavorite({
                        type: "headline",
                        symbol: activeSymbol,
                        title: article.title ?? "Untitled headline",
                        subtitle: article.source_name ?? "Unknown source",
                        url: article.link,
                      })
                    }
                    aria-label="Save headline to favorites"
                  >
                    {props.isFavorited({
                      type: "headline",
                      symbol: activeSymbol,
                      title: article.title ?? "Untitled headline",
                    }) ? (
                      <BookmarkCheck size={14} />
                    ) : (
                      <Bookmark size={14} />
                    )}
                  </button>
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() => {
                      props.setSearchSelection({
                        stamp: Date.now(),
                        companySymbol: activeSymbol,
                        newsSymbol: activeSymbol,
                      });
                      props.goToView("company");
                    }}
                    aria-label="Open company workspace"
                  >
                    <ArrowUpRight size={14} />
                  </button>
                </div>
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
                <div key={`${article.article_id ?? article.link ?? index}`} className="feed-item-wrap">
                  <a
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
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() =>
                      props.addFavorite({
                        type: "headline",
                        symbol: activeSymbol,
                        title: article.title ?? "Untitled article",
                        subtitle: `${article.sentiment ?? "unknown"} · ${article.source_name ?? "Unknown source"}`,
                        url: article.link,
                      })
                    }
                    aria-label="Save sentiment article to favorites"
                  >
                    {props.isFavorited({
                      type: "headline",
                      symbol: activeSymbol,
                      title: article.title ?? "Untitled article",
                    }) ? (
                      <BookmarkCheck size={14} />
                    ) : (
                      <Bookmark size={14} />
                    )}
                  </button>
                  <button
                    type="button"
                    className="favorite-icon-btn"
                    onClick={() => {
                      props.setSearchSelection({
                        stamp: Date.now(),
                        companySymbol: activeSymbol,
                        newsSymbol: activeSymbol,
                      });
                      props.goToView("company");
                    }}
                    aria-label="Open company workspace"
                  >
                    <ArrowUpRight size={14} />
                  </button>
                </div>
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

function SettingsView(props: {
  theme: Theme;
  onToggleTheme: () => void;
  favoritesCount: number;
  unreadNotifications: number;
}) {
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
          <span>{props.unreadNotifications} unread</span>
        </div>
        <div className="list-item">
          <p>Saved Favorites</p>
          <span>{props.favoritesCount} items</span>
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
