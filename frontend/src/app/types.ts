import type { LucideIcon } from "lucide-react";

export type ViewKey =
  | "dashboard"
  | "chat"
  | "compare"
  | "company"
  | "discovery"
  | "portfolio"
  | "domino"
  | "filings"
  | "timeline"
  | "news"
  | "money"
  | "performance"
  | "simulator"
  | "profile"
  | "settings"


export type Theme = "light" | "dark";
export type DataMode = "live" | "demo";
export type DashboardDensity = "comfortable" | "compact";

export interface DashboardPreferences {
  density: DashboardDensity;
  hiddenWidgets: string[];
}

export type NotificationCategory = "filing" | "risk" | "theme" | "system";
export type NotificationSeverity = "high" | "medium" | "low";

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  timestamp: string;
  read: boolean;
}

export type ToastTone = "info" | "success" | "warning";

export type ExplanationMode = "analyst" | "simple";

export interface AgentEvent {
  timestamp: string;
  agent: string;
  event: string;
}

export interface ToolCallEvent {
  timestamp: string;
  agent: string;
  tool: string;
  status: string;
}

export interface ChatMessage {
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

export interface ChatThread {
  id: string;
  title: string;
  pinned: boolean;
  createdAt: string;
  updatedAt: string;
  mode: ExplanationMode;
  messages: ChatMessage[];
  backendSessionId?: string;
}

export interface ToastItem {
  id: string;
  message: string;
  tone: ToastTone;
}

export interface SearchSelection {
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

export type CompanySearchSelection = {
  stamp: number;
  companySymbol: string;
  companyId?: string;
};

export type TimelineChatSearchSelection = {
  stamp: number;
  chatPrompt: string;
};

export type FilingsSearchSelection = {
  stamp: number;
  companySymbol: string;
  filingsSymbol: string;
};

export type NewsSearchSelection = {
  stamp: number;
  companySymbol: string;
  newsSymbol: string;
};

export type FavoriteType = "company" | "filing" | "headline";

export interface FavoriteItem {
  id: string;
  type: FavoriteType;
  symbol?: string;
  title: string;
  subtitle?: string;
  url?: string;
  createdAt: string;
}

export type AlertRuleType = "filing_event" | "risk_beta_above" | "theme_score_above";

export interface AlertRule {
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

export type GlobalSearchResultType = "company" | "theme" | "event" | "query";

export interface GlobalSearchResult {
  id: string;
  type: GlobalSearchResultType;
  title: string;
  subtitle: string;
  onSelect: () => void;
}

export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  keywords: string;
  action: () => void;
}

export interface NavItem {
  key: ViewKey;
  label: string;
  icon: LucideIcon;
  caption: string;
}
