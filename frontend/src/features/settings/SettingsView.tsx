import { PageHeader } from "../../shared/ui/PageHeader";

interface SettingsViewProps {
  theme: "light" | "dark";
  dataMode: "live" | "demo";
  onToggleTheme: () => void;
  onToggleDataMode: () => void;
  favoritesCount: number;
  unreadNotifications: number;
}

export function SettingsView(props: SettingsViewProps) {
  return (
    <section className="page-wrap">
      <PageHeader
        title="Workspace Settings"
        subtitle="Configure integrations, notifications, and assistant preferences."
        dataMode={props.dataMode}
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
        <div className="list-item">
          <p>Data Mode</p>
          <span>{props.dataMode === "demo" ? "Demo Data" : "Live API"}</span>
        </div>
      </div>

      <div className="chip-row">
        <button type="button" className="secondary-btn" onClick={props.onToggleTheme}>
          {props.theme === "dark" ? "Use Light Mode" : "Use Dark Mode"}
        </button>
        <button type="button" className="secondary-btn" onClick={props.onToggleDataMode}>
          {props.dataMode === "demo" ? "Switch to Live API" : "Switch to Demo Data"}
        </button>
      </div>
    </section>
  );
}
