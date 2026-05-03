import {
  Building2,
  Bot,
  CircleUserRound,
  Clock3,
  Compass,
  FileText,
  GitCompareArrows,
  Home,
  LayoutDashboard,
  Newspaper,
  Settings,
  Wallet,
} from "lucide-react";

import type {
  NavItem,
  NotificationItem,
} from "./types";

export const QUICK_QUERY_TEMPLATES = [
  "Summarize the latest filing impact for RELIANCE.",
  "Explain top portfolio risks in simple language.",
  "Compare sentiment momentum: TCS vs INFY.",
  "What changed in defense theme this week?",
  "Give a 5-point summary for my timeline events.",
  "Which themes look overheated right now?",
];

export const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
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

export const navItems: NavItem[] = [
  { key: "home", label: "Home", icon: Home, caption: "Personalised" },
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, caption: "Overview" },
  { key: "compare", label: "Compare", icon: GitCompareArrows, caption: "Side-by-side" },
  { key: "company", label: "Company", icon: Building2, caption: "Workspace" },
  { key: "chat", label: "Minerva Chat", icon: Bot, caption: "Copilot" },
  { key: "discovery", label: "Discovery", icon: Compass, caption: "Themes" },
  { key: "portfolio", label: "Portfolio", icon: Wallet, caption: "Exposure" },
  { key: "filings", label: "Filings", icon: FileText, caption: "Reports" },
  { key: "timeline", label: "Timeline", icon: Clock3, caption: "Feed" },
  { key: "news", label: "News", icon: Newspaper, caption: "Sentiment" },
  { key: "profile", label: "Profile", icon: CircleUserRound, caption: "Account" },
  { key: "settings", label: "Settings", icon: Settings, caption: "Preferences" },

];

export const THEME_STORAGE_KEY = "equityai-theme";
export const DATA_MODE_STORAGE_KEY = "equityai-data-mode";
export const NOTIFICATIONS_STORAGE_KEY = "equityai-notifications";
export const FAVORITES_STORAGE_KEY = "equityai-favorites";
export const DASHBOARD_PREFERENCES_KEY = "equityai-dashboard-preferences";
export const ALERT_RULES_STORAGE_KEY = "equityai-alert-rules";
export const CHAT_THREADS_STORAGE_KEY = "equityai-chat-threads";
export const CHAT_ACTIVE_THREAD_STORAGE_KEY = "equityai-chat-active-thread";

export const DEMO_BANNER_MSG =
  "Demo mode — showing cached data. Switch to Live API for real-time results.";
