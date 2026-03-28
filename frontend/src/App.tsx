import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bell,
  BookmarkCheck,
  Building2,
  Bot,
  CircleUserRound,
  Clock3,
  Compass,
  Command,
  Database,
  FileText,
  GitCompareArrows,
  LayoutDashboard,
  Moon,
  Newspaper,
  Search,
  Settings,
  ShieldAlert,
  Sparkles,
  Sun,
  Wallet,
} from "lucide-react";
import { DashboardView } from "./features/dashboard/DashboardView";
import { SettingsView } from "./features/settings/SettingsView";
import { DiscoveryView } from "./features/discovery/DiscoveryView";
import { TimelineView } from "./features/timeline/TimelineView";
import { PortfolioView } from "./features/portfolio/PortfolioView";
import { FilingsView } from "./features/filings/FilingsView";
import { NewsView } from "./features/news/NewsView";
import { ProfileView } from "./features/profile/ProfileView";
import { ComparisonWorkspaceView } from "./features/compare/ComparisonWorkspaceView";
import { ChatView } from "./features/chat/ChatView";
import { CompanyWorkspaceView } from "./features/company/CompanyWorkspaceView";
import { CommandPalette } from "./app/components/CommandPalette";
import { GlobalSearchOverlay } from "./app/components/GlobalSearchOverlay";
import { NotificationsPanel } from "./app/components/NotificationsPanel";
import { FavoritesPanel } from "./app/components/FavoritesPanel";
import { AlertRulesPanel } from "./app/components/AlertRulesPanel";
import { ToastStack } from "./app/components/ToastStack";

type ViewKey =
  | "dashboard"
  | "chat"
  | "compare"
  | "company"
  | "discovery"
  | "portfolio"
  | "filings"
  | "timeline"
  | "news"
  | "profile"
  | "settings";
type Theme = "light" | "dark";
type DataMode = "live" | "demo";
type DashboardDensity = "comfortable" | "compact";

interface DashboardPreferences {
  density: DashboardDensity;
  hiddenWidgets: string[];
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

interface AgentEvent {
  timestamp: string;
  agent: string;
  event: string;
}

interface ToolCallEvent {
  timestamp: string;
  agent: string;
  tool: string;
  status: string;
}

interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  sources?: string[];
  isThinking?: boolean;
  thinkingDurationSec?: number;
  executionPlan?: string[];
  agentEvents?: AgentEvent[];
  toolCalls?: ToolCallEvent[];
  attachedFile?: string;
}

interface ChatThread {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
  mode: ExplanationMode;
  messages: ChatMessage[];
  backendSessionId?: string;
}

interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

interface SearchSelection {
  stamp: number;
  companySymbol?: string;
  companyId?: string;
  compareSymbols?: string[];
  discoveryQuery?: string;
  discoveryTheme?: string;
  filingsSymbol?: string;
  newsSymbol?: string;
  timelineQuery?: string;
  timelineEventId?: string;
  chatPrompt?: string;
  reportScope?: "company" | "comparison";
  reportCompareSymbols?: string[];
}

type CompanySearchSelection = {
  stamp: number;
  companySymbol: string;
  companyId?: string;
};

type TimelineChatSearchSelection = {
  stamp: number;
  chatPrompt: string;
};

type FilingsSearchSelection = {
  stamp: number;
  companySymbol: string;
  filingsSymbol: string;
};

type NewsSearchSelection = {
  stamp: number;
  companySymbol: string;
  newsSymbol: string;
};

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
  { key: "compare", label: "Compare", icon: GitCompareArrows, caption: "Side-by-side" },
  { key: "company", label: "Company", icon: Building2, caption: "Workspace" },
  { key: "chat", label: "Iris Chat", icon: Bot, caption: "Copilot" },
  { key: "discovery", label: "Discovery", icon: Compass, caption: "Themes" },
  { key: "portfolio", label: "Portfolio", icon: Wallet, caption: "Exposure" },
  { key: "filings", label: "Filings", icon: FileText, caption: "Reports" },
  { key: "timeline", label: "Timeline", icon: Clock3, caption: "Feed" },
  { key: "news", label: "News", icon: Newspaper, caption: "Sentiment" },
  { key: "profile", label: "Profile", icon: CircleUserRound, caption: "Account" },
  { key: "settings", label: "Settings", icon: Settings, caption: "Preferences" },
];

const THEME_STORAGE_KEY = "equityai-theme";
const DATA_MODE_STORAGE_KEY = "equityai-data-mode";
const NOTIFICATIONS_STORAGE_KEY = "equityai-notifications";
const FAVORITES_STORAGE_KEY = "equityai-favorites";
const DASHBOARD_PREFERENCES_KEY = "equityai-dashboard-preferences";
const ALERT_RULES_STORAGE_KEY = "equityai-alert-rules";
const CHAT_THREADS_STORAGE_KEY = "equityai-chat-threads";
const CHAT_ACTIVE_THREAD_STORAGE_KEY = "equityai-chat-active-thread";

const DEMO_BANNER_MSG = "Demo mode — showing cached data. Switch to Live API for real-time results.";

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

function getInitialDataMode(): DataMode {
  const saved = window.localStorage.getItem(DATA_MODE_STORAGE_KEY);
  if (saved === "live" || saved === "demo") return saved;
  return "live";
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

function createInitialThread(promptText?: string): ChatThread {
  const now = new Date().toISOString();
  const messageSeed = promptText?.trim();

  const messages: ChatMessage[] = [
    {
      id: `assistant-${Date.now()}-intro`,
      role: "assistant",
      text: "Iris is ready. Start with filings, risk, sentiment, or a compare query.",
      sources: ["Workspace context", "Timeline feed", "Discovery themes"],
    },
  ];

  if (messageSeed) {
    messages.push({
      id: `user-${Date.now()}-seed`,
      role: "user",
      text: messageSeed,
    });
    messages.push({
      id: `assistant-${Date.now()}-seed`,
      role: "assistant",
      text: `Got it. I will analyze: "${messageSeed}" and structure the answer with risks, catalysts, and next checks.`,
      sources: ["Prompt intent parser", "Research heuristics"],
    });
  }

  return {
    id: `thread-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    title: messageSeed ? messageSeed.slice(0, 44) : "New thread",
    pinned: false,
    createdAt: now,
    updatedAt: now,
    mode: "analyst",
    messages,
  };
}

function getInitialChatThreads(): ChatThread[] {
  const saved = window.localStorage.getItem(CHAT_THREADS_STORAGE_KEY);
  if (!saved) return [createInitialThread()];

  try {
    const parsed = JSON.parse(saved) as ChatThread[];
    if (!Array.isArray(parsed) || !parsed.length) return [createInitialThread()];
    return parsed.filter((thread) => thread.id && Array.isArray(thread.messages));
  } catch {
    return [createInitialThread()];
  }
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [dataMode, setDataMode] = useState<DataMode>(getInitialDataMode);
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
  const [chatThreads, setChatThreads] = useState<ChatThread[]>(getInitialChatThreads);
  const [activeChatThreadId, setActiveChatThreadId] = useState("");
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
    window.localStorage.setItem(DATA_MODE_STORAGE_KEY, dataMode);
  }, [dataMode]);

  useEffect(() => {
    window.localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    window.localStorage.setItem(ALERT_RULES_STORAGE_KEY, JSON.stringify(alertRules));
  }, [alertRules]);

  useEffect(() => {
    window.localStorage.setItem(CHAT_THREADS_STORAGE_KEY, JSON.stringify(chatThreads));
  }, [chatThreads]);

  useEffect(() => {
    if (!activeChatThreadId) return;
    window.localStorage.setItem(CHAT_ACTIVE_THREAD_STORAGE_KEY, activeChatThreadId);
  }, [activeChatThreadId]);

  useEffect(() => {
    if (!chatThreads.length) {
      const thread = createInitialThread();
      setChatThreads([thread]);
      setActiveChatThreadId(thread.id);
      return;
    }

    if (activeChatThreadId && chatThreads.some((thread) => thread.id === activeChatThreadId)) {
      return;
    }

    const saved = window.localStorage.getItem(CHAT_ACTIVE_THREAD_STORAGE_KEY);
    if (saved && chatThreads.some((thread) => thread.id === saved)) {
      setActiveChatThreadId(saved);
      return;
    }

    setActiveChatThreadId(chatThreads[0].id);
  }, [activeChatThreadId, chatThreads]);

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

  const toggleDataMode = useCallback(() => {
    setDataMode((current) => {
      const next = current === "live" ? "demo" : "live";
      pushToast(next === "demo" ? "Demo mode enabled" : "Live API mode enabled", "info");
      return next;
    });
  }, [pushToast]);

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
    setAlertRules((current) =>
      current.map((rule) => ({ ...rule, lastCheckedAt: now }))
    );
    pushToast("Alert rules evaluated via backend", "info");
  }, [pushToast]);

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

    results.push({
      id: `search-${query}`,
      type: "company",
      title: `Search: ${query}`,
      subtitle: "Search company database",
      onSelect: () => {
        setSearchSelection({ stamp: Date.now(), discoveryQuery: query });
        goToView("discovery");
      },
    });

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
        id: "go-compare",
        label: "Go to Comparison Workspace",
        hint: "Navigation",
        keywords: "compare side by side symbols",
        action: () => {
          setSearchSelection({ stamp: Date.now(), compareSymbols: ["RELIANCE", "TCS"] });
          goToView("compare");
        },
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
        id: "toggle-data-mode",
        label: dataMode === "demo" ? "Switch to Live API Mode" : "Switch to Demo Data Mode",
        hint: "Data",
        keywords: "demo mock live api data mode",
        action: () => {
          toggleDataMode();
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
      dataMode,
      theme,
      toggleDataMode,
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
            dataMode={dataMode}
            preferences={dashboardPreferences}
            onToggleDensity={toggleDashboardDensity}
            onToggleWidget={toggleDashboardWidget}
            onResetPreferences={resetDashboardPreferences}
          />
        );
      case "compare":
        return (
          <ComparisonWorkspaceView
            dataMode={dataMode}
            pushToast={pushToast}
            searchSelection={searchSelection}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "company":
        return (
          <CompanyWorkspaceView
            dataMode={dataMode}
            pushToast={pushToast}
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={goToView}
            setSearchSelection={setSearchSelection}
          />
        );
      case "chat":
        return (
          <ChatView
            searchSelection={searchSelection}
            dataMode={dataMode}
            threads={chatThreads}
            activeThreadId={activeChatThreadId}
            setThreads={setChatThreads}
            setActiveThreadId={setActiveChatThreadId}
            createInitialThread={createInitialThread}
            demoBannerMessage={DEMO_BANNER_MSG}
          />
        );
      case "discovery":
        return (
          <DiscoveryView
            dataMode={dataMode}
            searchSelection={searchSelection}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={(view) => goToView(view)}
            setSearchSelection={(selection: CompanySearchSelection) =>
              setSearchSelection((current) => ({ ...current, ...selection }))
            }
          />
        );
      case "portfolio":
        return <PortfolioView dataMode={dataMode} />;
      case "filings":
        return (
          <FilingsView
            searchSelection={searchSelection}
            dataMode={dataMode}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={(view) => goToView(view)}
            setSearchSelection={(selection: FilingsSearchSelection) =>
              setSearchSelection((current) => ({ ...current, ...selection }))
            }
          />
        );
      case "timeline":
        return (
          <TimelineView
            dataMode={dataMode}
            searchSelection={searchSelection}
            goToView={(view) => goToView(view)}
            setSearchSelection={(selection: TimelineChatSearchSelection) =>
              setSearchSelection((current) => ({ ...current, ...selection }))
            }
          />
        );
      case "news":
        return (
          <NewsView
            searchSelection={searchSelection}
            dataMode={dataMode}
            addFavorite={addFavorite}
            isFavorited={isFavorited}
            goToView={(view) => goToView(view)}
            setSearchSelection={(selection: NewsSearchSelection) =>
              setSearchSelection((current) => ({ ...current, ...selection }))
            }
          />
        );
      case "profile":
        return (
          <ProfileView
            dataMode={dataMode}
            theme={theme}
            onToggleTheme={toggleTheme}
            onToggleDataMode={toggleDataMode}
            pushToast={pushToast}
          />
        );
      case "settings":
        return (
          <SettingsView
            theme={theme}
            dataMode={dataMode}
            onToggleTheme={toggleTheme}
            onToggleDataMode={toggleDataMode}
            favoritesCount={favorites.length}
            unreadNotifications={unreadCount}
          />
        );
      default:
        return (
          <DashboardView
            dataMode={dataMode}
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
    activeChatThreadId,
    dashboardPreferences,
    dataMode,
    favorites.length,
    goToView,
    isFavorited,
    pushToast,
    resetDashboardPreferences,
    searchSelection,
    chatThreads,
    theme,
    toggleDashboardDensity,
    toggleDashboardWidget,
    toggleDataMode,
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

        <button type="button" className="theme-toggle" onClick={toggleDataMode}>
          <Database size={15} />
          <span>{dataMode === "demo" ? "Mode: Demo Data" : "Mode: Live API"}</span>
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
          <div className="status-pill">{dataMode === "demo" ? "Demo mode active" : "Live API mode"}</div>
        </div>
      </aside>

      <main className="main-panel">{page}</main>

      <CommandPalette
        open={paletteOpen}
        query={paletteQuery}
        activeIndex={paletteActiveIndex}
        commands={filteredCommands}
        inputRef={paletteInputRef}
        setQuery={setPaletteQuery}
        setActiveIndex={setPaletteActiveIndex}
        onClose={closePalette}
      />

      <GlobalSearchOverlay
        open={globalSearchOpen}
        query={globalSearchQuery}
        activeIndex={globalSearchIndex}
        results={globalSearchResults}
        inputRef={globalSearchInputRef}
        setQuery={setGlobalSearchQuery}
        setActiveIndex={setGlobalSearchIndex}
        onClose={closeGlobalSearch}
      />

      <NotificationsPanel
        open={notificationsOpen}
        filter={notificationFilter}
        notifications={filteredNotifications}
        onClose={() => setNotificationsOpen(false)}
        onFilterChange={setNotificationFilter}
        onMarkAllRead={markAllNotificationsRead}
        onMarkRead={markNotificationRead}
        onDismiss={dismissNotification}
      />

      <FavoritesPanel
        open={favoritesOpen}
        filter={favoriteFilter}
        favorites={filteredFavorites}
        onClose={() => setFavoritesOpen(false)}
        onFilterChange={setFavoriteFilter}
        onOpenFavorite={handleFavoriteSelect}
        onRemoveFavorite={removeFavorite}
      />

      <AlertRulesPanel
        open={alertRulesOpen}
        rules={alertRules}
        ruleName={ruleName}
        ruleType={ruleType}
        ruleSymbol={ruleSymbol}
        ruleThreshold={ruleThreshold}
        onClose={() => setAlertRulesOpen(false)}
        onRuleNameChange={setRuleName}
        onRuleTypeChange={setRuleType}
        onRuleSymbolChange={setRuleSymbol}
        onRuleThresholdChange={setRuleThreshold}
        onCreateRule={createAlertRule}
        onRunCheck={runAlertRulesCheck}
        onToggleRule={toggleAlertRule}
        onDeleteRule={deleteAlertRule}
      />

      <ToastStack toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
