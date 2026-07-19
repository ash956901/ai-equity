import { useState } from "react";
import { AppShell } from "./components/shell/AppShell";
import { NAV, type ViewKey } from "./routes";
import { DashboardView } from "./views/DashboardView";
import { DominoView } from "./views/DominoView";
import { MinervaView } from "./views/MinervaView";
import { PortfolioView } from "./views/PortfolioView";
import { DiscoveryView } from "./views/DiscoveryView";
import { CompanyView } from "./views/CompanyView";
import { CompareView } from "./views/CompareView";
import { WatchlistView } from "./views/WatchlistView";
import { NewsView } from "./views/NewsView";
import { FilingsView } from "./views/FilingsView";
import { SimulatorView } from "./views/SimulatorView";
import { ProfileView } from "./views/ProfileView";
import { SettingsView } from "./views/SettingsView";
import { AuthView, OnboardingView } from "./views/AuthView";
import { Placeholder } from "./views/Placeholder";
import { useAuth } from "./lib/auth";
import { Icon } from "./components/Icon";

export default function App() {
  const { user, loading, needsOnboarding } = useAuth();
  const [view, setView] = useState<ViewKey>("dashboard");
  const [companyId, setCompanyId] = useState<string | null>(null);
  const label = NAV.find((n) => n.key === view)?.label ?? view;

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-0 flex items-center justify-center">
        <Icon name="progress_activity" className="text-primary text-[32px] animate-spin" />
      </div>
    );
  }

  if (!user) return <AuthView />;
  if (needsOnboarding) return <OnboardingView />;

  function openCompany(id: string) {
    setCompanyId(id);
    setView("company");
  }

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
      case "discovery":
        return <DiscoveryView onOpenCompany={openCompany} />;
      case "company":
        return <CompanyView companyId={companyId} onOpenCompany={openCompany} />;
      case "compare":
        return <CompareView />;
      case "watchlist":
        return <WatchlistView onOpenCompany={openCompany} />;
      case "news":
        return <NewsView />;
      case "filings":
        return <FilingsView />;
      case "simulator":
        return <SimulatorView />;
      case "profile":
        return <ProfileView />;
      case "settings":
        return <SettingsView />;
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
