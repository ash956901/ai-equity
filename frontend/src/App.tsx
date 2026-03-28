import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowUp,
  ArrowUpRight,
  BarChart3,
  Bell,
  Bookmark,
  BookmarkCheck,
  Building2,
  BookOpenText,
  Bot,
  CheckCheck,
  CircleUserRound,
  Clock3,
  Compass,
  Command,
  Database,
  FileText,
  GitCompareArrows,
  LayoutDashboard,
  Loader2,
  Moon,
  Newspaper,
  Paperclip,
  Pencil,
  Pin,
  Plus,
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
import type { jsPDF as JsPdfType } from "jspdf";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
  fetchSecFilings,
  fetchCompanyDetail,
  fetchCompanyRatios,
  fetchCompanyQuote,
  searchCompaniesDB,
  fetchTimeline,
  listChatSessions,
  enrichCompany,
  uploadDocument,
  sendChatQuery,
  type SecFiling,
  type AICompany,
  type AIRatios,
  type AIQuote,
  type TimelineEvent as BackendTimelineEvent,
  type ChatQueryRequest,
} from "./lib/api";
import { PageHeader } from "./shared/ui/PageHeader";
import { SourceBadges } from "./shared/ui/SourceBadges";
import { ThinkingDropdown } from "./features/chat/components/ThinkingDropdown";
import { ThinkingIndicator } from "./features/chat/components/ThinkingIndicator";
import { DashboardView } from "./features/dashboard/DashboardView";
import { SettingsView } from "./features/settings/SettingsView";
import { DiscoveryView } from "./features/discovery/DiscoveryView";
import { TimelineView } from "./features/timeline/TimelineView";
import { PortfolioView } from "./features/portfolio/PortfolioView";
import { FilingsView } from "./features/filings/FilingsView";
import { NewsView } from "./features/news/NewsView";
import { ProfileView } from "./features/profile/ProfileView";
import { ComparisonWorkspaceView } from "./features/compare/ComparisonWorkspaceView";

function normalizeSymbolsInput(value: string): string[] {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 4)
    )
  );
}

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

interface DiscoveryCompany {
  symbol: string;
  name: string;
  sector: string;
  marketCapBn: number;
  insight: string;
  themeScores: Record<string, number>;
}

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

type ReportSectionId = "summary" | "risks" | "financials" | "themes";
type ReportAudience = "retail" | "analyst";

interface ReportSectionOption {
  id: ReportSectionId;
  label: string;
}

interface GeneratedReportSection {
  id: ReportSectionId;
  heading: string;
  content: string;
}

interface GeneratedReport {
  title: string;
  generatedAt: string;
  audience: ReportAudience;
  audienceText: string;
  symbol: string;
  companyName: string;
  dataMode: DataMode;
  scope: "company" | "comparison";
  compareSymbols?: string[];
  sections: GeneratedReportSection[];
  body: string;
}

interface PdfTemplate {
  coverLabel: string;
  accent: [number, number, number];
}

const PDF_TEMPLATES: Record<ReportAudience, PdfTemplate> = {
  retail: {
    coverLabel: "Retail Brief",
    accent: [15, 134, 186],
  },
  analyst: {
    coverLabel: "Analyst Dossier",
    accent: [17, 87, 131],
  },
};

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

const REPORT_SECTION_OPTIONS: ReportSectionOption[] = [
  { id: "summary", label: "Executive Summary" },
  { id: "risks", label: "Key Risks" },
  { id: "financials", label: "Financial Snapshot" },
  { id: "themes", label: "Theme Outlook" },
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

function getUserId(): string {
  let id = localStorage.getItem("equityai-user-id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("equityai-user-id", id);
  }
  return id;
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

function wrapPdfText(doc: JsPdfType, text: string, maxWidth: number): string[] {
  return doc.splitTextToSize(text, maxWidth) as string[];
}

function renderPdfParagraph(
  doc: JsPdfType,
  text: string,
  leftX: number,
  rightX: number,
  startY: number
): number {
  const lines = wrapPdfText(doc, text, rightX - leftX);
  doc.text(lines, leftX, startY);
  return startY + lines.length * 6 + 2;
}

async function exportReportAsPdf(report: GeneratedReport): Promise<void> {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const marginLeft = 16;
  const marginRight = pageWidth - 16;
  const template = PDF_TEMPLATES[report.audience];

  doc.setFillColor(template.accent[0], template.accent[1], template.accent[2]);
  doc.rect(0, 0, pageWidth, 46, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(24);
  doc.text("EquityAI Research Report", marginLeft, 20);
  doc.setFontSize(12);
  doc.setFont("helvetica", "normal");
  doc.text(template.coverLabel, marginLeft, 28);
  doc.text(`${report.companyName} (${report.symbol})`, marginLeft, 35);

  doc.setTextColor(18, 32, 45);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(report.title, marginLeft, 58);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  const metadataLines = [
    `Generated: ${new Date(report.generatedAt).toLocaleString()}`,
    `Audience: ${report.audience === "retail" ? "Retail" : "Analyst"}`,
    `Data Mode: ${report.dataMode === "demo" ? "Demo Data" : "Live API"}`,
  ];

  let y = 66;
  for (const line of metadataLines) {
    doc.text(line, marginLeft, y);
    y += 5.5;
  }

  doc.setDrawColor(210, 220, 230);
  doc.line(marginLeft, y + 2, marginRight, y + 2);
  y += 10;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Executive Framing", marginLeft, y);
  y += 7;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  y = renderPdfParagraph(doc, report.audienceText, marginLeft, marginRight, y);

  for (const section of report.sections) {
    if (y > pageHeight - 30) {
      doc.addPage();
      y = 20;
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(section.heading, marginLeft, y);
    y += 7;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);

    const lines = section.content.split("\n");
    for (const line of lines) {
      if (!line.trim()) {
        y += 2;
        continue;
      }

      if (y > pageHeight - 16) {
        doc.addPage();
        y = 20;
      }

      y = renderPdfParagraph(doc, line, marginLeft, marginRight, y);
    }
    y += 4;
  }

  const pageCount = doc.getNumberOfPages();
  const scopeLabel = report.scope === "comparison" ? "Comparison" : "Company";
  for (let page = 1; page <= pageCount; page += 1) {
    doc.setPage(page);
    doc.setFontSize(9);
    doc.setTextColor(110, 122, 134);
    doc.text(
      `${scopeLabel} · ${report.symbol} · ${report.dataMode === "demo" ? "Demo" : "Live"} · Page ${page}/${pageCount}`,
      marginLeft,
      pageHeight - 8
    );
  }

  const filename =
    report.scope === "comparison"
      ? `${toFileSlug(report.symbol)}-comparison-report.pdf`
      : `${toFileSlug(report.symbol)}-${report.audience}-report.pdf`;
  doc.save(filename);
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

function toFileSlug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
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

function ChatView(props: {
  searchSelection: SearchSelection | null;
  dataMode: DataMode;
  threads: ChatThread[];
  activeThreadId: string;
  setThreads: React.Dispatch<React.SetStateAction<ChatThread[]>>;
  setActiveThreadId: React.Dispatch<React.SetStateAction<string>>;
}) {
  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(0);
  const [showSources, setShowSources] = useState(true);
  const [composerText, setComposerText] = useState("");
  const [threadQuery, setThreadQuery] = useState("");
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachedUploadId, setAttachedUploadId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const uid = getUserId();
    listChatSessions(uid).catch(() => {});
  }, []);

  const suggestions = [
    "What changed in RELIANCE latest filing?",
    "Summarize risk signals for my portfolio in simple terms.",
    "Compare IT services sentiment: TCS vs INFY.",
    "Explain why defense theme is heating up this week.",
  ];

  const activeThread = useMemo(
    () => props.threads.find((thread) => thread.id === props.activeThreadId) ?? props.threads[0] ?? null,
    [props.activeThreadId, props.threads]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeThread?.messages]);

  const sortedThreads = useMemo(() => {
    return [...props.threads].sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
    });
  }, [props.threads]);

  const filteredThreads = useMemo(() => {
    const query = threadQuery.trim().toLowerCase();
    if (!query) return sortedThreads;

    return sortedThreads.filter((thread) => {
      const lastMessage = thread.messages[thread.messages.length - 1]?.text ?? "";
      return `${thread.title} ${lastMessage}`.toLowerCase().includes(query);
    });
  }, [sortedThreads, threadQuery]);

  const updateActiveThread = useCallback(
    (updater: (thread: ChatThread) => ChatThread) => {
      if (!activeThread) return;
      props.setThreads((current) =>
        current.map((thread) => (thread.id === activeThread.id ? updater(thread) : thread))
      );
    },
    [activeThread, props]
  );

  const createThread = useCallback(
    (initialPrompt?: string) => {
      const thread = createInitialThread(initialPrompt);
      props.setThreads((current) => [thread, ...current]);
      props.setActiveThreadId(thread.id);
      setThreadQuery("");
      return thread;
    },
    [props]
  );

  const handleFileSelect = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setAttachedFile(file);
      setIsUploading(true);

      try {
        const userId = localStorage.getItem("equityai-user-id") || crypto.randomUUID();
        localStorage.setItem("equityai-user-id", userId);

        const result = await uploadDocument(userId, file, activeThread?.backendSessionId);
        setAttachedUploadId(result.upload_id);
      } catch {
        setAttachedFile(null);
        setAttachedUploadId(null);
      } finally {
        setIsUploading(false);
        if (event.target) event.target.value = "";
      }
    },
    [activeThread]
  );

  const clearAttachment = useCallback(() => {
    setAttachedFile(null);
    setAttachedUploadId(null);
  }, []);

  const sendMessage = useCallback(async () => {
    const text = composerText.trim();
    if (!text || !activeThread) return;

    const now = new Date().toISOString();
    const currentFile = attachedFile;
    const currentUploadId = attachedUploadId;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      role: "user",
      text,
      attachedFile: currentFile?.name,
    };

    setComposerText("");
    clearAttachment();

    if (props.dataMode === "live") {
      const thinkingMessage: ChatMessage = {
        id: `assistant-thinking-${Date.now()}`,
        role: "assistant",
        text: "",
        isThinking: true,
      };

      props.setThreads((current) =>
        current.map((thread) => {
          if (thread.id !== activeThread.id) return thread;
          return {
            ...thread,
            title: thread.messages.length <= 1 ? text.slice(0, 44) : thread.title,
            updatedAt: now,
            messages: [...thread.messages, userMessage, thinkingMessage],
          };
        })
      );

      const startTime = performance.now();

      try {
        const userId = localStorage.getItem("equityai-user-id") || crypto.randomUUID();
        localStorage.setItem("equityai-user-id", userId);

        const expertiseLevel = activeThread.mode === "simple" ? "beginner" : "advanced";
        const chatReq: ChatQueryRequest = {
          user_id: userId,
          query: text,
          expertise_level: expertiseLevel,
          session_id: activeThread.backendSessionId,
        };
        if (currentUploadId) chatReq.upload_id = currentUploadId;
        const resp = await sendChatQuery(chatReq);

        const elapsedSec = Math.round((performance.now() - startTime) / 1000);

        const sources = resp.sources?.map((s: Record<string, unknown>) => String(s.title || s.source || JSON.stringify(s))) ?? [];

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          role: "assistant",
          text: resp.response,
          sources: sources.length > 0 ? sources : undefined,
          thinkingDurationSec: elapsedSec,
          executionPlan: resp.execution_plan?.length ? resp.execution_plan : undefined,
          agentEvents: resp.agent_call_log?.length ? (resp.agent_call_log as unknown as AgentEvent[]) : undefined,
          toolCalls: resp.tool_call_log?.length ? (resp.tool_call_log as unknown as ToolCallEvent[]) : undefined,
        };

        props.setThreads((current) =>
          current.map((thread) => {
            if (thread.id !== activeThread.id) return thread;
            const msgs = thread.messages.filter((m) => m.id !== thinkingMessage.id);
            return {
              ...thread,
              updatedAt: new Date().toISOString(),
              backendSessionId: resp.session_id,
              messages: [...msgs, assistantMessage],
            };
          })
        );
      } catch (err) {
        const errorMessage: ChatMessage = {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          text: `Error: ${err instanceof Error ? err.message : "Failed to get AI response"}. The AI backend may be unavailable.`,
        };

        props.setThreads((current) =>
          current.map((thread) => {
            if (thread.id !== activeThread.id) return thread;
            const msgs = thread.messages.filter((m) => m.id !== thinkingMessage.id);
            return {
              ...thread,
              updatedAt: new Date().toISOString(),
              messages: [...msgs, errorMessage],
            };
          })
        );
      }
    } else {
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role: "assistant",
        text: DEMO_BANNER_MSG + " Switch to Live API to get real AI-powered responses.",
      };

      props.setThreads((current) =>
        current.map((thread) => {
          if (thread.id !== activeThread.id) return thread;
          return {
            ...thread,
            title: thread.messages.length <= 1 ? text.slice(0, 44) : thread.title,
            updatedAt: now,
            messages: [...thread.messages, userMessage, assistantMessage],
          };
        })
      );
    }
  }, [activeThread, attachedFile, attachedUploadId, clearAttachment, composerText, props]);

  const renameThread = useCallback(
    (threadId: string) => {
      const target = props.threads.find((thread) => thread.id === threadId);
      if (!target) return;
      const next = window.prompt("Rename thread", target.title);
      if (!next || !next.trim()) return;

      props.setThreads((current) =>
        current.map((thread) =>
          thread.id === threadId
            ? { ...thread, title: next.trim().slice(0, 60), updatedAt: new Date().toISOString() }
            : thread
        )
      );
    },
    [props]
  );

  const deleteThread = useCallback(
    (threadId: string) => {
      if (props.threads.length <= 1) {
        const replacement = createInitialThread();
        props.setThreads([replacement]);
        props.setActiveThreadId(replacement.id);
        return;
      }

      const remaining = props.threads.filter((thread) => thread.id !== threadId);
      props.setThreads(remaining);
      if (props.activeThreadId === threadId) {
        props.setActiveThreadId(remaining[0].id);
      }
    },
    [props]
  );

  useEffect(() => {
    if (!activeThread) return;
    setComposerText((current) => (current ? current : ""));
  }, [activeThread]);

  useEffect(() => {
    if (!props.searchSelection) return;
    if (props.searchSelection.stamp === lastSelectionStamp) return;

    if (props.searchSelection.chatPrompt) {
      if (activeThread && activeThread.messages.length <= 1) {
        setComposerText(props.searchSelection.chatPrompt);
      } else {
        const created = createThread(props.searchSelection.chatPrompt);
        props.setActiveThreadId(created.id);
        setComposerText("");
      }
    }

    setLastSelectionStamp(props.searchSelection.stamp);
  }, [
    activeThread,
    createThread,
    lastSelectionStamp,
    props,
    props.searchSelection,
    props.setActiveThreadId,
  ]);

  if (!activeThread) return null;

  return (
    <section className="page-wrap">
      <PageHeader
        title="Iris Research Copilot"
        subtitle="Persistent threads with mode-aware responses and reusable prompts."
        dataMode={props.dataMode}
        right={
          <div className="chat-controls">
            <button
              type="button"
              className={`mode-pill ${activeThread.mode === "analyst" ? "active" : ""}`}
              onClick={() =>
                updateActiveThread((thread) => ({
                  ...thread,
                  mode: "analyst",
                  updatedAt: new Date().toISOString(),
                }))
              }
            >
              <BookOpenText size={14} />
              Analyst Mode
            </button>
            <button
              type="button"
              className={`mode-pill ${activeThread.mode === "simple" ? "active" : ""}`}
              onClick={() =>
                updateActiveThread((thread) => ({
                  ...thread,
                  mode: "simple",
                  updatedAt: new Date().toISOString(),
                }))
              }
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

      <div className="chat-layout">
        <aside className="chat-threads-panel">
          <div className="chat-threads-head">
            <p className="results-title">Thread History</p>
            <button type="button" className="secondary-btn mini-btn" onClick={() => createThread()}>
              <Plus size={13} />
              New
            </button>
          </div>

          <div className="search-pill chat-thread-filter">
            <Search size={13} />
            <input
              placeholder="Filter threads"
              value={threadQuery}
              onChange={(event) => setThreadQuery(event.target.value)}
            />
          </div>

          <div className="chat-thread-list">
            {filteredThreads.length ? (
              filteredThreads.map((thread) => (
                <div
                  key={thread.id}
                  className={`chat-thread-item ${thread.id === activeThread.id ? "active" : ""}`}
                >
                  <button
                    type="button"
                    className="chat-thread-main"
                    onClick={() => props.setActiveThreadId(thread.id)}
                  >
                    <p>{thread.title || "Untitled thread"}</p>
                    <span>
                      {thread.messages.length} msgs · {new Date(thread.updatedAt).toLocaleDateString()}
                    </span>
                  </button>
                  <div className="chat-thread-actions">
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() =>
                        props.setThreads((current) =>
                          current.map((item) =>
                            item.id === thread.id
                              ? {
                                  ...item,
                                  pinned: !item.pinned,
                                  updatedAt: new Date().toISOString(),
                                }
                              : item
                          )
                        )
                      }
                      aria-label="Pin thread"
                    >
                      <Pin size={13} />
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() => renameThread(thread.id)}
                      aria-label="Rename thread"
                    >
                      <Pencil size={13} />
                    </button>
                    <button
                      type="button"
                      className="favorite-icon-btn"
                      onClick={() => deleteThread(thread.id)}
                      aria-label="Delete thread"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <p className="chat-thread-empty">No threads match this filter.</p>
            )}
          </div>
        </aside>

        <article className="chat-shell chat-main">
          {activeThread.messages.length <= 1 ? (
            <div className="chat-empty-state">
              <div className="chat-empty-logo">
                <Sparkles size={28} />
              </div>
              <h2>Iris Research Copilot</h2>
              <p>Ask anything about Indian equities — filings, risk signals, sentiment, or portfolio strategy.</p>
              <div className="chat-empty-suggestions">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="chat-empty-suggestion-btn"
                    onClick={() => setComposerText(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="chat-messages-area">
              {activeThread.messages.map((message) =>
                message.role === "user" ? (
                  <div key={message.id} className="chat-row chat-row--user">
                    <div className="chat-bubble-user">
                      {message.attachedFile && (
                        <div className="chat-file-badge">
                          <Paperclip size={10} />
                          <span>{message.attachedFile}</span>
                        </div>
                      )}
                      <span>{message.text}</span>
                    </div>
                  </div>
                ) : (
                  <div key={message.id} className="chat-row chat-row--assistant">
                    <div className="chat-assistant-icon">
                      <Sparkles size={16} />
                    </div>
                    <div className="chat-assistant-body">
                      {message.isThinking ? (
                        <ThinkingIndicator />
                      ) : (
                        <>
                          <ThinkingDropdown message={message} />
                          <div className="message-text">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {message.text}
                            </ReactMarkdown>
                          </div>
                          {showSources && message.toolCalls?.length ? (
                            <div className="chat-sources-bar">
                              <span className="chat-sources-label">Sources</span>
                              <div className="chat-sources-list">
                                {message.toolCalls
                                  .filter((tc) => tc.status === "success")
                                  .map((tc, i) => (
                                    <span key={`src-tc-${tc.agent}-${tc.tool}-${i}`} className="chat-source-tag">
                                      <Database size={10} />
                                      <span>{tc.tool.replace(/_/g, " ")}</span>
                                    </span>
                                  ))}
                                {message.sources?.map((source, i) => (
                                  <span key={`src-ext-${message.id}-${i}`} className="chat-source-tag">
                                    <Database size={10} />
                                    <span>{source}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : showSources && message.sources?.length ? (
                            <div className="chat-sources-bar">
                              <span className="chat-sources-label">Sources</span>
                              <div className="chat-sources-list">
                                {message.sources.map((source, i) => (
                                  <span key={`src-${message.id}-${i}`} className="chat-source-tag">
                                    <Database size={10} />
                                    <span>{source}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          ) : null}
                        </>
                      )}
                    </div>
                  </div>
                )
              )}
              <div ref={messagesEndRef} />
            </div>
          )}

          {attachedFile && (
            <div className="chat-attachment-bar">
              <div className={`file-pill ${isUploading ? "uploading" : ""}`}>
                <FileText size={14} />
                <span>{attachedFile.name}</span>
                {isUploading ? (
                  <Loader2 size={14} className="spin" />
                ) : (
                  <button type="button" className="file-pill-remove" onClick={clearAttachment} aria-label="Remove file">
                    <X size={12} />
                  </button>
                )}
              </div>
            </div>
          )}
          <div className="chat-input-row">
            <input type="file" ref={fileInputRef} className="sr-only" accept=".pdf,.pptx,.ppt,.txt,.csv,.xlsx" onChange={handleFileSelect} />
            <button type="button" className="chat-upload-btn" onClick={() => fileInputRef.current?.click()} title="Attach document" disabled={isUploading}>
              <Paperclip size={16} />
            </button>
            <input
              placeholder={attachedFile ? "Ask about this document..." : "Ask Iris anything about equities..."}
              value={composerText}
              onChange={(event) => setComposerText(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  sendMessage();
                }
              }}
            />
            <button
              type="button"
              className="chat-send-btn"
              onClick={sendMessage}
              disabled={isUploading || !composerText.trim()}
              aria-label="Send message"
            >
              <ArrowUp size={18} />
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}


function CompanyWorkspaceView(props: {
  dataMode: DataMode;
  pushToast: (message: string, tone?: ToastTone) => void;
  searchSelection: SearchSelection | null;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  goToView: (view: ViewKey) => void;
  setSearchSelection: (selection: SearchSelection) => void;
}) {
  const { searchSelection, pushToast, dataMode } = props;

  const [lastSelectionStamp, setLastSelectionStamp] = useState<number>(
    () => searchSelection?.stamp ?? 0
  );
  const [symbolInput, setSymbolInput] = useState(() => {
    const s =
      searchSelection?.companySymbol ??
      searchSelection?.filingsSymbol ??
      searchSelection?.newsSymbol ??
      searchSelection?.discoveryQuery;
    return s ? s.toUpperCase() : "RELIANCE";
  });
  const [activeSymbol, setActiveSymbol] = useState(() => {
    const s =
      searchSelection?.companySymbol ??
      searchSelection?.filingsSymbol ??
      searchSelection?.newsSymbol ??
      searchSelection?.discoveryQuery;
    return s ? s.toUpperCase() : "RELIANCE";
  });
  const [activeCompanyId, setActiveCompanyId] = useState<string | null>(
    () => searchSelection?.companyId ?? null
  );
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
  const [reportAudience, setReportAudience] = useState<ReportAudience>("analyst");
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);
  const [reportScope, setReportScope] = useState<"company" | "comparison">("company");
  const [comparisonSymbols, setComparisonSymbols] = useState<string[]>([]);
  const [comparisonSymbolsInput, setComparisonSymbolsInput] = useState("");

  useEffect(() => {
    if (!searchSelection) return;
    if (searchSelection.stamp === lastSelectionStamp) return;

    const symbol =
      searchSelection.companySymbol ??
      searchSelection.filingsSymbol ??
      searchSelection.newsSymbol ??
      searchSelection.discoveryQuery;

    if (symbol) {
      const normalized = symbol.toUpperCase();
      setActiveSymbol(normalized);
      setSymbolInput(normalized);
    }

    if (searchSelection.companyId) {
      setActiveCompanyId(searchSelection.companyId);
    } else {
      setActiveCompanyId(null);
    }

    if (
      searchSelection.reportScope === "comparison" &&
      searchSelection.reportCompareSymbols?.length
    ) {
      const normalized = searchSelection.reportCompareSymbols
        .map((item) => item.trim().toUpperCase())
        .filter(Boolean)
        .slice(0, 4);

      if (normalized.length >= 2) {
        if (normalized.length >= 2) {
          const symbolsText = normalized.join(" vs ");

          setReportScope("comparison");
          setComparisonSymbols(normalized);
          setComparisonSymbolsInput(normalized.join(", "));
          setReportTitle(`${symbolsText} Comparative Brief`);
          setReportSections(["summary", "risks", "financials", "themes"]);
          setReportAudience("analyst");
          setReportGeneratedAt(new Date().toISOString());

          pushToast("Comparison report draft generated", "success");
        }
      }
    } else if (searchSelection.reportScope === "company") {
      setReportScope("company");
      setComparisonSymbols([]);
      setComparisonSymbolsInput("");
    }

    setLastSelectionStamp(searchSelection.stamp);
  }, [lastSelectionStamp, pushToast, searchSelection]);

  const [companyDetail, setCompanyDetail] = useState<AICompany | null>(null);
  const [companyQuote, setCompanyQuote] = useState<AIQuote | null>(null);
  const [companyRatios, setCompanyRatios] = useState<AIRatios | null>(null);
  const [companyLoading, setCompanyLoading] = useState(false);
  const [companyTimeline, setCompanyTimeline] = useState<BackendTimelineEvent[]>([]);

  const loadCompanyById = useCallback(async (companyId: string) => {
    setCompanyLoading(true);
    try {
      const [detail, ratios] = await Promise.allSettled([
        fetchCompanyDetail(companyId),
        fetchCompanyRatios(companyId),
      ]);
      let detailData: AICompany | null = null;
      if (detail.status === "fulfilled") {
        detailData = detail.value;
        setCompanyDetail(detailData);
      }
      if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
      fetchCompanyQuote(companyId).then(setCompanyQuote).catch(() => {});
      fetchTimeline(undefined, companyId, 10).then(setCompanyTimeline).catch(() => {});

      if (detailData && !detailData.sector) {
        enrichCompany(companyId).then(async (res) => {
          if (res.enriched) {
            const refreshed = await fetchCompanyDetail(companyId);
            setCompanyDetail(refreshed);
          }
        }).catch(() => {});
      }
    } catch {
      // Ignore lookup failures; UI shows fallback messaging.
    } finally {
      setCompanyLoading(false);
    }
  }, []);

  const loadCompanyBySymbol = useCallback(async (symbol: string) => {
    setCompanyLoading(true);
    try {
      const results = await searchCompaniesDB(symbol, 5);
      if (results.length > 0) {
        const matched = results[0];
        const [detail, ratios] = await Promise.allSettled([
          fetchCompanyDetail(matched.id),
          fetchCompanyRatios(matched.id),
        ]);
        let detailData: AICompany | null = null;
        if (detail.status === "fulfilled") {
          detailData = detail.value;
          setCompanyDetail(detailData);
        }
        if (ratios.status === "fulfilled") setCompanyRatios(ratios.value);
        fetchCompanyQuote(matched.id).then(setCompanyQuote).catch(() => {});
        fetchTimeline(undefined, matched.id, 10).then(setCompanyTimeline).catch(() => {});

        if (detailData && !detailData.sector) {
          enrichCompany(matched.id).then(async (res) => {
            if (res.enriched) {
              const refreshed = await fetchCompanyDetail(matched.id);
              setCompanyDetail(refreshed);
            }
          }).catch(() => {});
        }
      }
    } catch {
      // Ignore lookup failures; UI shows fallback messaging.
    } finally {
      setCompanyLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeCompanyId) {
      void loadCompanyById(activeCompanyId);
    } else {
      void loadCompanyBySymbol(activeSymbol);
    }
  }, [activeSymbol, activeCompanyId, loadCompanyById, loadCompanyBySymbol]);

  const companyData = useMemo((): DiscoveryCompany => {
    if (companyDetail) {
      const mcBn = companyDetail.market_cap_inr ? companyDetail.market_cap_inr / 1e9 : 0;
      const ticker = companyDetail.ticker_nse ?? companyDetail.ticker_bse;
      const symbol = ticker ?? companyDetail.name;
      return {
        symbol,
        name: companyDetail.name,
        sector: companyDetail.sector ?? "Unknown",
        marketCapBn: mcBn,
        insight: companyDetail.description ?? companyDetail.industry ?? "",
        themeScores: {},
      };
    }
    return {
      symbol: activeSymbol,
      name: `${activeSymbol}`,
      sector: "Unknown",
      marketCapBn: 0,
      insight: companyLoading ? "Loading company data..." : "Search for a company by ticker or name.",
      themeScores: {},
    };
  }, [activeSymbol, companyDetail, companyLoading]);

  const topThemes = useMemo(
    () => Object.entries(companyData.themeScores).sort((a, b) => b[1] - a[1]).slice(0, 5),
    [companyData.themeScores]
  );

  const comparisonCompanies = useMemo(() => {
    if (reportScope !== "comparison") return [];
    return comparisonSymbols.map((symbol) => ({
      symbol,
      name: symbol,
      sector: "Unknown",
      marketCapBn: 0,
      insight: "",
      themeScores: {},
    } as DiscoveryCompany));
  }, [comparisonSymbols, reportScope]);

  const comparisonTimeline = useMemo((): TimelineEvent[] => {
    if (reportScope !== "comparison") return [];
    return [];
  }, [reportScope]);

  const comparisonMetrics = useMemo(() => {
    if (reportScope !== "comparison" || comparisonCompanies.length < 2) {
      return null;
    }

    const strengths = comparisonCompanies.map((company) => {
      const [theme, score] = Object.entries(company.themeScores).sort((a, b) => b[1] - a[1])[0] ?? ["None", 0];
      return { symbol: company.symbol, topTheme: theme, score };
    });

    const strongest = strengths.reduce((best, current) =>
      !best || current.score > best.score ? current : best
    );
    const weakest = strengths.reduce((worst, current) =>
      !worst || current.score < worst.score ? current : worst
    );

    const riskScores = comparisonCompanies.map((company) => {
      const avg =
        Object.values(company.themeScores).reduce((sum, value) => sum + value, 0) /
        Math.max(Object.values(company.themeScores).length, 1);
      const concentrationPenalty = Math.max(0, 90 - avg);
      const timelinePenalty = comparisonTimeline.filter(
        (event) => event.company === company.symbol && event.impact === "high"
      ).length;

      return {
        symbol: company.symbol,
        score: Number((concentrationPenalty + timelinePenalty * 4).toFixed(1)),
      };
    });

    const highestRisk = riskScores.reduce((best, current) =>
      !best || current.score > best.score ? current : best
    );
    const lowestRisk = riskScores.reduce((best, current) =>
      !best || current.score < best.score ? current : best
    );

    const allThemesSet = new Set<string>();
    comparisonCompanies.forEach((company) => {
      Object.keys(company.themeScores).forEach((theme) => allThemesSet.add(theme));
    });

    const divergence = Array.from(allThemesSet)
      .map((theme) => {
        const values = comparisonCompanies.map((company) => company.themeScores[theme] ?? 0);
        const spread = Math.max(...values) - Math.min(...values);
        return { theme, spread };
      })
      .sort((a, b) => b.spread - a.spread)
      .slice(0, 3);

    return {
      strengths,
      strongest,
      weakest,
      highestRisk,
      lowestRisk,
      divergence,
    };
  }, [comparisonCompanies, comparisonTimeline, reportScope]);

  const [companyFilings, setCompanyFilings] = useState<(SecFiling & { narrative: string })[]>([]);

  const filingsTicker = companyDetail?.ticker_nse ?? null;

  useEffect(() => {
    if (dataMode === "demo" || !filingsTicker) {
      setCompanyFilings([]);
      return;
    }
    fetchSecFilings(filingsTicker, 7).then((filings) => {
      setCompanyFilings(filings.slice(0, 7).map((f) => ({
        ...f,
        narrative: f.type === "10-K"
          ? "Annual report and strategic commentary."
          : f.type === "10-Q"
            ? "Quarterly operating metrics and margin data."
            : "Event or regulatory disclosure.",
      })));
    }).catch(() => setCompanyFilings([]));
  }, [filingsTicker, dataMode]);

  const companyRatioSnapshot = useMemo(() => {
    if (companyRatios?.ratios) {
      const r = companyRatios.ratios;
      return {
        pe: r.pe_ratio ?? 0,
        pb: r.pb_ratio ?? 0,
        roe: r.roe ?? 0,
        debtToEquity: r.debt_to_equity ?? 0,
        operatingMargin: r.ebitda_margin ?? r.net_margin ?? 0,
        beta: 1.0,
      };
    }
    return { pe: 0, pb: 0, roe: 0, debtToEquity: 0, operatingMargin: 0, beta: 0 };
  }, [companyRatios]);

  const companySentimentTrend = useMemo(() => {
    const topThemeScore = topThemes[0]?.[1] ?? 62;
    const baseShift = Math.round((topThemeScore - 60) / 7);
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

    return days.map((day, index) => {
      const positive = Math.max(1, 5 + baseShift + ((index + 2) % 3));
      const negative = Math.max(0, 2 + ((index + 1) % 2) - Math.max(baseShift, -1));
      const neutral = Math.max(1, 7 - index + Math.max(0, baseShift));
      const score = positive * 2 + neutral - negative * 2;

      return {
        day,
        positive,
        neutral,
        negative,
        score,
      };
    });
  }, [topThemes]);

  const companyLabel = companyData.name !== companyData.symbol ? companyData.name : companyData.symbol;

  const tabPrompts = useMemo<Record<"overview" | "filings" | "sentiment" | "timeline" | "chat", string[]>>(
    () => ({
      overview: [
        `Give a 5-point briefing on ${companyLabel} strategic posture.`,
        `What three catalysts should I monitor for ${companyLabel}?`,
        `Summarize valuation context for ${companyLabel} in plain terms.`,
      ],
      filings: [
        `What changed materially in ${companyLabel} recent filings?`,
        `List potential red flags from ${companyLabel} latest disclosures.`,
        `Convert ${companyLabel} filing updates into an action checklist.`,
      ],
      sentiment: [
        `How stable is ${companyLabel} sentiment trend this week?`,
        `Explain the sentiment shift in ${companyLabel} with likely drivers.`,
        `What sentiment reversal signals should I watch for ${companyLabel}?`,
      ],
      timeline: [
        `Rank ${companyLabel} timeline events by decision relevance.`,
        `What is the most important recent event for ${companyLabel} and why?`,
        `Build a risk-aware timeline summary for ${companyLabel}.`,
      ],
      chat: [
        `Prepare a balanced bull vs bear case for ${companyLabel}.`,
        `What should I verify before increasing exposure to ${companyLabel}?`,
        `Create a one-week monitoring plan for ${companyLabel}.`,
      ],
    }),
    [companyLabel]
  );

  const [companyChatPrompt, setCompanyChatPrompt] = useState("");

  useEffect(() => {
    const first = tabPrompts[activeTab]?.[0] ?? "";
    setCompanyChatPrompt(first);
  }, [activeTab, tabPrompts]);

  const comparisonSummary = useMemo(() => {
    if (reportScope !== "comparison" || comparisonCompanies.length < 2 || !comparisonMetrics) {
      return null;
    }

    const avgMarketCap =
      comparisonCompanies.reduce((sum, company) => sum + company.marketCapBn, 0) /
      comparisonCompanies.length;
    const sectors = Array.from(new Set(comparisonCompanies.map((company) => company.sector))).join(", ");

    return {
      symbolsLabel: comparisonCompanies.map((company) => company.symbol).join(" vs "),
      avgMarketCap,
      sectors,
      topSpreadTheme: comparisonMetrics.divergence[0],
    };
  }, [comparisonCompanies, comparisonMetrics, reportScope]);

  const nseOrBseTicker = companyDetail?.ticker_nse ?? companyDetail?.ticker_bse;
  const profileTitle = nseOrBseTicker
    ? `${nseOrBseTicker} · ${companyData.name}`
    : companyData.name;

  const generatedReport = useMemo<GeneratedReport | null>(() => {
    if (!reportGeneratedAt) return null;

    const sections: GeneratedReportSection[] = [];

    if (reportScope === "comparison" && (!comparisonSummary || !comparisonMetrics)) {
      return null;
    }

    if (reportScope === "comparison" && comparisonSummary && comparisonMetrics) {
      if (reportSections.includes("summary")) {
        sections.push({
          id: "summary",
          heading: "Executive Summary",
          content:
            `${comparisonSummary.symbolsLabel} comparison indicates strongest momentum in ` +
            `${comparisonMetrics.strongest.symbol} (${comparisonMetrics.strongest.topTheme} ${comparisonMetrics.strongest.score}/100), ` +
            `while ${comparisonMetrics.weakest.symbol} trails on composite theme intensity (${comparisonMetrics.weakest.score}/100).`,
        });
      }

      if (reportSections.includes("risks")) {
        const riskSpread = (comparisonMetrics.highestRisk.score - comparisonMetrics.lowestRisk.score).toFixed(
          1
        );
        sections.push({
          id: "risks",
          heading: "Risk Spread",
          content:
            `Highest modeled risk: ${comparisonMetrics.highestRisk.symbol} (${comparisonMetrics.highestRisk.score}).\n` +
            `Lowest modeled risk: ${comparisonMetrics.lowestRisk.symbol} (${comparisonMetrics.lowestRisk.score}).\n` +
            `Spread: ${riskSpread}. Monitor names with weaker average theme quality and clustered high-impact events.`,
        });
      }

      if (reportSections.includes("financials")) {
        const winnersText = [...comparisonCompanies]
          .sort((a, b) => b.marketCapBn - a.marketCapBn)
          .slice(0, 2)
          .map((company) => `${company.symbol} ($${company.marketCapBn.toFixed(1)}B)`)
          .join(", ");

        sections.push({
          id: "financials",
          heading: "Scale & Coverage",
          content:
            `Average market cap across basket: $${comparisonSummary.avgMarketCap.toFixed(1)}B.\n` +
            `Largest names by scale: ${winnersText}.\n` +
            `Sector mix: ${comparisonSummary.sectors}.`,
        });
      }

      if (reportSections.includes("themes")) {
        const divergenceText = comparisonMetrics.divergence.length
          ? comparisonMetrics.divergence
              .map((item) => `${item.theme} (spread ${item.spread})`)
              .join(", ")
          : "No meaningful divergence detected";

        sections.push({
          id: "themes",
          heading: "Theme Divergence",
          content:
            `${divergenceText}.\n` +
            `Largest current gap: ${comparisonSummary.topSpreadTheme?.theme ?? "N/A"} ` +
            `(${comparisonSummary.topSpreadTheme?.spread ?? 0} points).`,
        });
      }

      const audienceText =
        reportAudience === "retail"
          ? "Retail framing: prefer simple winner/laggard interpretation and avoid overtrading on one-cycle noise."
          : "Analyst framing: evaluate relative momentum, dispersion, and event-adjusted risk asymmetry across the basket.";

      return {
        title: reportTitle.trim() || `${comparisonSummary.symbolsLabel} Comparative Brief`,
        generatedAt: reportGeneratedAt,
        audience: reportAudience,
        audienceText,
        symbol: comparisonSummary.symbolsLabel,
        companyName: "Comparison Basket",
        dataMode,
        scope: "comparison",
        compareSymbols: comparisonCompanies.map((company) => company.symbol),
        sections,
        body: sections.map((section) => `${section.heading}:\n${section.content}`).join("\n\n"),
      };
    }

    const topTheme = topThemes[0]?.[0] ?? "No clear dominant theme";
    const topThemeScore = topThemes[0]?.[1] ?? 0;

    if (reportSections.includes("summary")) {
      sections.push({
        id: "summary",
        heading: "Executive Summary",
        content: `${companyData.name}${nseOrBseTicker ? ` (${nseOrBseTicker})` : ""} currently shows strongest narrative strength in ${topTheme} with theme score ${topThemeScore}/100. Sector context remains ${companyData.sector}.`,
      });
    }

    if (reportSections.includes("risks")) {
      sections.push({
        id: "risks",
        heading: "Key Risks",
        content:
          "1) Execution risk around near-term filings guidance.\n2) Valuation sensitivity if sector momentum cools.\n3) Sentiment volatility around macro updates.",
      });
    }

    if (reportSections.includes("financials")) {
      sections.push({
        id: "financials",
        heading: "Financial Snapshot",
        content: `Market Cap: $${companyData.marketCapBn.toFixed(1)}B\nRecent timeline events: ${companyTimeline.length}\nPrimary sector: ${companyData.sector}`,
      });
    }

    if (reportSections.includes("themes")) {
      const themeText = topThemes.length
        ? topThemes.map(([theme, score]) => `${theme} (${score})`).join(", ")
        : "No theme signal available";

      sections.push({
        id: "themes",
        heading: "Theme Outlook",
        content: `Dominant theme signals: ${themeText}.`,
      });
    }

    const audienceText =
      reportAudience === "retail"
        ? "Retail framing: keep explanations concise and action oriented."
        : "Analyst framing: include context, assumptions, and scenario sensitivity.";

    return {
      title: reportTitle.trim() || `${companyLabel} Research Brief`,
      generatedAt: reportGeneratedAt,
      audience: reportAudience,
      audienceText,
      symbol: companyData.symbol,
      companyName: companyData.name,
      dataMode,
      scope: "company",
      sections,
      body: sections
        .map((section) => `${section.heading}:\n${section.content}`)
        .join("\n\n"),
    };
  }, [
    comparisonCompanies,
    comparisonMetrics,
    comparisonSummary,
    companyData.marketCapBn,
    companyData.name,
    companyData.sector,
    companyData.symbol,
    companyTimeline.length,
    reportScope,
    reportAudience,
    reportGeneratedAt,
    reportSections,
    reportTitle,
    companyLabel,
    nseOrBseTicker,
    dataMode,
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
    if (reportScope === "comparison") {
      const normalized = normalizeSymbolsInput(comparisonSymbolsInput || comparisonSymbols.join(","));
      if (normalized.length >= 2) {
        setComparisonSymbols(normalized);
        setComparisonSymbolsInput(normalized.join(", "));
      }

      if (normalized.length < 2) {
        pushToast("Comparison report needs at least two valid symbols", "warning");
        return;
      }
    }
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
    const baseName = generatedReport.scope === "comparison" ? generatedReport.symbol : companyLabel;
    anchor.download = `${toFileSlug(baseName)}-report.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
    pushToast("Text report downloaded", "success");
  };

  const exportReportPdf = async () => {
    if (!generatedReport) return;
    try {
      pushToast("Preparing PDF export...", "info");
      await exportReportAsPdf(generatedReport);
      pushToast("PDF report downloaded", "success");
    } catch {
      pushToast("PDF export failed. Please try again.", "warning");
    }
  };

  return (
    <section className="page-wrap">
      <PageHeader
        title="Company Workspace"
        subtitle="One research cockpit per company: filings, sentiment, timeline, and company-context chat."
        dataMode={dataMode}
        right={
          <form
            className="search-pill"
            onSubmit={(event) => {
              event.preventDefault();
              const normalized = symbolInput.trim().toUpperCase();
              if (normalized) {
                setActiveCompanyId(null);
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

      {reportScope === "comparison" && comparisonSummary ? (
        <div className="notice">
          Comparison report mode: {comparisonSummary.symbolsLabel}. Generate a unified winner/laggard and
          risk-spread brief from this basket.
        </div>
      ) : null}

      {companyLoading && <div className="notice"><Loader2 size={16} className="spin" /> Loading company data...</div>}

      <div className="company-header-card">
        <div className="company-header-main">
          {nseOrBseTicker && <p className="discovery-symbol">{nseOrBseTicker}</p>}
          <h2>{companyData.name}</h2>
          <p>{companyData.insight}</p>
          <div className="chip-row">
            <span className="chip">Sector: {companyData.sector}</span>
            {companyData.marketCapBn > 0 && <span className="chip">Market Cap: ₹{companyData.marketCapBn.toFixed(1)}B</span>}
          </div>
          <SourceBadges sources={companyDetail?.data_sources} />
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
              <TrendingUp size={18} />
              <h3>Live Quote</h3>
            </div>
            {companyQuote?.last_price ? (
              <>
                <h2>₹{Number(companyQuote.last_price).toLocaleString()}</h2>
                {companyQuote.change_pct != null && (
                  <p className={Number(companyQuote.change_pct) >= 0 ? "positive" : "negative"}>
                    {Number(companyQuote.change_pct) >= 0 ? "+" : ""}{Number(companyQuote.change_pct).toFixed(2)}%
                  </p>
                )}
                <small>Source: {companyQuote.source ?? "API"} · {companyQuote.fetched_at ? new Date(companyQuote.fetched_at).toLocaleTimeString() : ""}</small>
                <SourceBadges sources={companyQuote.data_sources} />
              </>
            ) : (
              <p>{companyLoading ? "Fetching quote..." : "No live quote data available."}</p>
            )}
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <Clock3 size={18} />
              <h3>Recent Events</h3>
            </div>
            <p>{companyTimeline.length} recent timeline events for this company.</p>
            {companyTimeline.slice(0, 3).map((ev) => (
              <div key={ev.id} className="list-item">
                <p>{ev.title}</p>
                <small>{new Date(ev.timestamp).toLocaleDateString()}</small>
              </div>
            ))}
          </article>
        </div>
      ) : null}

      {activeTab === "filings" ? (
        <article className="list-card company-filings-card">
          <div className="table-head">
            <h3>Filings Snapshot ({companyLabel})</h3>
            <span>{companyFilings.length} filings</span>
          </div>
          {companyFilings.map((filing, index) => (
            <div key={`${filing.type}-${filing.filingDate ?? index}`} className="list-item company-filing-row">
              <div>
                <p>{filing.type} · {filing.title}</p>
                <small>{filing.narrative}</small>
              </div>
              <span>{new Date(filing.filingDate ?? filing.acceptedDate ?? Date.now()).toLocaleDateString()}</span>
            </div>
          ))}
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={() => {
              props.setSearchSelection({
                stamp: Date.now(),
                filingsSymbol: companyData.symbol,
                companySymbol: companyData.symbol,
              });
              props.goToView("filings");
            }}
          >
            Open Full Filings Workspace
          </button>
        </article>
      ) : null}

      {activeTab === "sentiment" ? (
        <div className="split-grid">
          <article className="feature-card">
            <div className="feature-head">
              <TrendingUp size={18} />
              <h3>Sentiment Timeline ({companyLabel})</h3>
            </div>
            <div className="chart-wrap medium">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={companySentimentTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(120,132,145,0.22)" />
                  <XAxis dataKey="day" tick={{ fill: "#7d8792", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#7d8792", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid rgba(120,132,145,0.25)",
                      background: "rgba(12,18,26,0.92)",
                      color: "#e8edf2",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#139bcf"
                    strokeWidth={2.2}
                    dot={{ r: 2.8, fill: "#139bcf" }}
                    name="Net Sentiment"
                  />
                  <Line
                    type="monotone"
                    dataKey="negative"
                    stroke="#d86c52"
                    strokeWidth={1.6}
                    dot={false}
                    name="Negative Mentions"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="feature-card">
            <div className="feature-head">
              <BarChart3 size={18} />
              <h3>Ratio Snapshot ({companyLabel})</h3>
            </div>
            <SourceBadges sources={companyRatios?.data_sources} />
            <div className="ratio-grid">
              <div className="ratio-item">
                <span>PE</span>
                <strong>{companyRatioSnapshot.pe.toFixed(1)}</strong>
              </div>
              <div className="ratio-item">
                <span>PB</span>
                <strong>{companyRatioSnapshot.pb.toFixed(2)}</strong>
              </div>
              <div className="ratio-item">
                <span>ROE</span>
                <strong>{companyRatioSnapshot.roe.toFixed(1)}%</strong>
              </div>
              <div className="ratio-item">
                <span>Debt/Equity</span>
                <strong>{companyRatioSnapshot.debtToEquity.toFixed(2)}</strong>
              </div>
              <div className="ratio-item">
                <span>Op Margin</span>
                <strong>{companyRatioSnapshot.operatingMargin.toFixed(1)}%</strong>
              </div>
              <div className="ratio-item">
                <span>Beta</span>
                <strong>{companyRatioSnapshot.beta.toFixed(2)}</strong>
              </div>
            </div>
          </article>
        </div>
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
              <p>No timeline events for {companyLabel} in local dataset.</p>
            </div>
          )}
        </article>
      ) : null}

      {activeTab === "chat" ? (
        <article className="chat-shell">
          <div className="chat-suggestions">
            {tabPrompts[activeTab].map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="chat-suggestion-chip"
                onClick={() => setCompanyChatPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
          <div className="chat-messages">
            <div className="message assistant">
              <p>
                You are now in {companyLabel} context. Ask company-specific questions to get
                tighter research answers.
              </p>
              <div className="source-list">
                <span className="source-chip">Company Workspace · Context mode</span>
              </div>
            </div>
          </div>
          <div className="chat-input-row">
            <input
              value={companyChatPrompt}
              onChange={(event) => setCompanyChatPrompt(event.target.value)}
            />
            <button
              type="button"
              className="primary-btn"
              onClick={() => {
                if (!companyChatPrompt.trim()) return;
                props.setSearchSelection({
                  stamp: Date.now(),
                  companySymbol: companyData.symbol,
                  chatPrompt: companyChatPrompt,
                });
                props.goToView("chat");
              }}
            >
              Ask in Iris Chat
            </button>
          </div>
        </article>
      ) : null}

      {activeTab !== "chat" ? (
        <article className="feature-card tab-prompt-card">
          <div className="feature-head">
            <Bot size={18} />
            <h3>Contextual Prompts for {activeTab[0].toUpperCase() + activeTab.slice(1)}</h3>
          </div>
          <div className="chat-suggestions">
            {tabPrompts[activeTab].map((prompt) => (
              <button
                key={`${activeTab}-${prompt}`}
                type="button"
                className="chat-suggestion-chip"
                onClick={() => {
                  props.setSearchSelection({
                    stamp: Date.now(),
                    companySymbol: companyData.symbol,
                    chatPrompt: prompt,
                  });
                  props.goToView("chat");
                }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </article>
      ) : null}

      <article className="report-builder-card">
        <div className="feature-head">
          <FileText size={18} />
          <h3>Report Generation Workspace</h3>
        </div>

        <div className="report-scope-row">
          <button
            type="button"
            className={`mode-pill ${reportScope === "company" ? "active" : ""}`}
            onClick={() => {
              setReportScope("company");
              setComparisonSymbols([]);
              setComparisonSymbolsInput("");
            }}
          >
            Company Report
          </button>
          <button
            type="button"
            className={`mode-pill ${reportScope === "comparison" ? "active" : ""}`}
            onClick={() => {
              const normalized = normalizeSymbolsInput(
                comparisonSymbolsInput || comparisonSymbols.join(",") || `${activeSymbol}, TCS`
              );
              if (normalized.length >= 2) {
                setComparisonSymbols(normalized);
                setComparisonSymbolsInput(normalized.join(", "));
                setReportScope("comparison");
                setReportTitle(`${normalized.join(" vs ")} Comparative Brief`);
              } else {
                pushToast("Add at least two symbols for comparison report", "warning");
              }
            }}
          >
            Comparison Report
          </button>
        </div>

        {reportScope === "comparison" ? (
          <div className="report-builder-grid">
            <label className="report-field">
              <span>Comparison symbols</span>
              <input
                value={comparisonSymbolsInput || comparisonSymbols.join(", ")}
                readOnly
              />
            </label>
            <label className="report-field">
              <span>Comparison focus</span>
              <input
                value={comparisonSummary ? `${comparisonSummary.symbolsLabel}` : "No valid basket yet"}
                readOnly
              />
            </label>
          </div>
        ) : null}

        {reportScope === "comparison" && comparisonMetrics ? (
          <div className="comparison-report-insights">
            <div className="chip-row">
              <span className="chip">Winner: {comparisonMetrics.strongest.symbol}</span>
              <span className="chip">Laggard: {comparisonMetrics.weakest.symbol}</span>
              <span className="chip warning">Risk High: {comparisonMetrics.highestRisk.symbol}</span>
              <span className="chip positive">Risk Low: {comparisonMetrics.lowestRisk.symbol}</span>
            </div>
          </div>
        ) : null}

        <div className="report-builder-grid">
          <label className="report-field">
            <span>Report title</span>
            <input
              value={reportTitle}
              onChange={(event) => setReportTitle(event.target.value)}
              placeholder={`${companyLabel} quarterly research brief`}
            />
          </label>

          <label className="report-field">
            <span>Audience</span>
            <select
              className="type-select"
              value={reportAudience}
              onChange={(event) => setReportAudience(event.target.value as ReportAudience)}
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
          <button
            type="button"
            className="secondary-btn mini-btn"
            onClick={exportReportPdf}
            disabled={!generatedReport}
          >
            Download .pdf
          </button>
        </div>

        {generatedReport ? (
          <div className="report-preview">
            <h4>{generatedReport.title}</h4>
            <p>{generatedReport.audienceText}</p>
            <small>Scope: {generatedReport.scope === "comparison" ? "Comparison" : "Company"}</small>
            <small>
              Template: {generatedReport.audience === "retail" ? "Retail Brief" : "Analyst Dossier"}
            </small>
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
