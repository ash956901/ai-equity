import {
  Bell,
  Moon,
  Sparkles,
  Sun,
} from "lucide-react";

import { OmniSearch } from "../../components/OmniSearch";
import { navItems } from "../constants";
import type { ViewKey } from "../types";

interface SidebarShellProps {
  activeView: ViewKey;
  unreadCount: number;
  theme: "light" | "dark";
  onOpenNotifications: () => void;
  onToggleTheme: () => void;
  onGoToView: (view: ViewKey) => void;
  onPickCompany?: (ticker: string, companyId?: string) => void;
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

      {props.onPickCompany ? (
        <div className="side-panel__omnisearch">
          <OmniSearch onPick={props.onPickCompany} />
        </div>
      ) : null}

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

      <button type="button" className="theme-toggle" onClick={props.onToggleTheme}>
        {props.theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        <span>{props.theme === "dark" ? "Switch to light" : "Switch to dark"}</span>
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
    </aside>
  );
}
