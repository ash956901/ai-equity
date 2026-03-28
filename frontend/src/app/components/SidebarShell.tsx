import {
  Bell,
  BookmarkCheck,
  Command,
  Database,
  Moon,
  Search,
  ShieldAlert,
  Sparkles,
  Sun,
} from "lucide-react";

import { navItems } from "../constants";
import type { ViewKey } from "../types";

interface SidebarShellProps {
  activeView: ViewKey;
  unreadCount: number;
  activeRulesCount: number;
  favoritesCount: number;
  theme: "light" | "dark";
  dataMode: "live" | "demo";
  onOpenNotifications: () => void;
  onOpenAlertRules: () => void;
  onOpenFavorites: () => void;
  onClearFavorites: () => void;
  onToggleTheme: () => void;
  onToggleDataMode: () => void;
  onOpenPalette: () => void;
  onOpenGlobalSearch: () => void;
  onGoToView: (view: ViewKey) => void;
}

export function SidebarShell(props: SidebarShellProps) {
  return (
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
        onClick={props.onOpenNotifications}
        aria-label="Open notifications"
      >
        <span className="notification-bell-left">
          <Bell size={15} />
          Notifications
        </span>
        <span className={`notification-count ${props.unreadCount ? "has-unread" : ""}`}>
          {props.unreadCount}
        </span>
      </button>

      <button
        type="button"
        className="notification-bell"
        onClick={props.onOpenAlertRules}
        aria-label="Open alert rules"
      >
        <span className="notification-bell-left">
          <ShieldAlert size={15} />
          Alert Rules
        </span>
        <span className={`notification-count ${props.activeRulesCount ? "has-unread" : ""}`}>
          {props.activeRulesCount}
        </span>
      </button>

      <button
        type="button"
        className="favorites-bell"
        onClick={props.onOpenFavorites}
        aria-label="Open favorites"
      >
        <span className="notification-bell-left">
          <BookmarkCheck size={15} />
          Favorites
        </span>
        <span className="notification-count">{props.favoritesCount}</span>
      </button>

      <button
        type="button"
        className="secondary-btn mini-btn favorites-clear-btn"
        onClick={props.onClearFavorites}
      >
        Clear Favorites
      </button>

      <button type="button" className="theme-toggle" onClick={props.onToggleTheme}>
        {props.theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        <span>{props.theme === "dark" ? "Switch to light" : "Switch to dark"}</span>
      </button>

      <button type="button" className="theme-toggle" onClick={props.onToggleDataMode}>
        <Database size={15} />
        <span>{props.dataMode === "demo" ? "Mode: Demo Data" : "Mode: Live API"}</span>
      </button>

      <button type="button" className="command-shortcut" onClick={props.onOpenPalette}>
        <span className="command-shortcut-left">
          <Command size={14} />
          Command Palette
        </span>
        <span className="kbd-chip">Ctrl/Cmd + K</span>
      </button>

      <button type="button" className="global-search-shortcut" onClick={props.onOpenGlobalSearch}>
        <span className="command-shortcut-left">
          <Search size={14} />
          Global Search
        </span>
        <span className="kbd-chip">Ctrl/Cmd + J</span>
      </button>

      <nav className="nav-stack">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = props.activeView === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => props.onGoToView(item.key)}
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
        <div className="status-pill">{props.dataMode === "demo" ? "Demo mode active" : "Live API mode"}</div>
      </div>
    </aside>
  );
}
