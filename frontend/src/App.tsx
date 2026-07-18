import { useState } from "react";
import { AppShell } from "./components/shell/AppShell";
import { NAV, type ViewKey } from "./routes";
import { DashboardView } from "./views/DashboardView";
import { DominoView } from "./views/DominoView";
import { MinervaView } from "./views/MinervaView";
import { PortfolioView } from "./views/PortfolioView";
import { Placeholder } from "./views/Placeholder";

export default function App() {
  const [view, setView] = useState<ViewKey>("dashboard");
  const label = NAV.find((n) => n.key === view)?.label ?? view;

  function renderView() {
    switch (view) {
      case "dashboard":
        return <DashboardView onNavigate={setView} />;
      case "minerva":
        return <MinervaView />;
      case "portfolio":
        return <PortfolioView />;
      case "domino":
        return <DominoView />;
      default:
        return <Placeholder title={label} />;
    }
  }

  return (
    <AppShell active={view} onNavigate={setView}>
      {renderView()}
    </AppShell>
  );
}
