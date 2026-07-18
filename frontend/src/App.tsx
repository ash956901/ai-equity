import { useState } from "react";
import { AppShell } from "./components/shell/AppShell";
import { NAV, type ViewKey } from "./routes";
import { DashboardView } from "./views/DashboardView";
import { Placeholder } from "./views/Placeholder";

export default function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const label = NAV.find((n) => n.key === view)?.label ?? view;

  return (
    <AppShell active={view} onNavigate={setView}>
      {view === "dashboard" ? <DashboardView onNavigate={setView} /> : <Placeholder title={label} />}
    </AppShell>
  );
}
