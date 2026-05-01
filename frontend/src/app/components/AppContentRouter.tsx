import type { Dispatch, SetStateAction } from "react";

import { ChatView } from "../../features/chat/ChatView";
import { ComparisonWorkspaceView } from "../../features/compare/ComparisonWorkspaceView";
import { CompanyWorkspaceView } from "../../features/company/CompanyWorkspaceView";
import { DashboardView } from "../../features/dashboard/DashboardView";
import { DiscoveryView } from "../../features/discovery/DiscoveryView";
import { FilingsView } from "../../features/filings/FilingsView";
import { NewsView } from "../../features/news/NewsView";
import { PortfolioView } from "../../features/portfolio/PortfolioView";
import { ProfileView } from "../../features/profile/ProfileView";
import { SettingsView } from "../../features/settings/SettingsView";

import { TimelineView } from "../../features/timeline/TimelineView";
import type {
  ChatThread,
  CompanySearchSelection,
  DashboardPreferences,
  DataMode,
  FavoriteItem,
  FilingsSearchSelection,
  NewsSearchSelection,
  SearchSelection,
  Theme,
  TimelineChatSearchSelection,
  ToastTone,
  ViewKey,
} from "../types";

interface AppContentRouterProps {
  activeView: ViewKey;
  dataMode: DataMode;
  dashboardPreferences: DashboardPreferences;
  onToggleDashboardDensity: () => void;
  onToggleDashboardWidget: (widgetId: string) => void;
  onResetDashboardPreferences: () => void;
  pushToast: (message: string, tone?: ToastTone) => void;
  searchSelection: SearchSelection | null;
  goToView: (view: ViewKey) => void;
  setSearchSelection: Dispatch<SetStateAction<SearchSelection | null>>;
  addFavorite: (favorite: Omit<FavoriteItem, "id" | "createdAt">) => void;
  isFavorited: (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => boolean;
  chatThreads: ChatThread[];
  activeChatThreadId: string;
  setChatThreads: Dispatch<SetStateAction<ChatThread[]>>;
  setActiveChatThreadId: Dispatch<SetStateAction<string>>;
  createInitialThread: (promptText?: string) => ChatThread;
  demoBannerMessage: string;
  theme: Theme;
  onToggleTheme: () => void;
  onToggleDataMode: () => void;
  favoritesCount: number;
  unreadCount: number;
}

export function AppContentRouter(props: AppContentRouterProps) {
  switch (props.activeView) {
    case "dashboard":
      return (
        <DashboardView
          dataMode={props.dataMode}
          preferences={props.dashboardPreferences}
          onToggleDensity={props.onToggleDashboardDensity}
          onToggleWidget={props.onToggleDashboardWidget}
          onResetPreferences={props.onResetDashboardPreferences}
        />
      );
    case "compare":
      return (
        <ComparisonWorkspaceView
          dataMode={props.dataMode}
          pushToast={props.pushToast}
          searchSelection={props.searchSelection}
          goToView={props.goToView}
          setSearchSelection={props.setSearchSelection}
        />
      );
    case "company":
      return (
        <CompanyWorkspaceView
          dataMode={props.dataMode}
          pushToast={props.pushToast}
          searchSelection={props.searchSelection}
          addFavorite={props.addFavorite}
          isFavorited={props.isFavorited}
          goToView={props.goToView}
          setSearchSelection={props.setSearchSelection}
        />
      );
    case "chat":
      return (
        <ChatView
          searchSelection={props.searchSelection}
          dataMode={props.dataMode}
          threads={props.chatThreads}
          activeThreadId={props.activeChatThreadId}
          setThreads={props.setChatThreads}
          setActiveThreadId={props.setActiveChatThreadId}
          createInitialThread={props.createInitialThread}
          demoBannerMessage={props.demoBannerMessage}
        />
      );
    case "discovery":
      return (
        <DiscoveryView
          dataMode={props.dataMode}
          searchSelection={props.searchSelection}
          addFavorite={props.addFavorite}
          isFavorited={props.isFavorited}
          goToView={(view) => props.goToView(view)}
          setSearchSelection={(selection: CompanySearchSelection) =>
            props.setSearchSelection((current) => ({ ...current, ...selection }))
          }
        />
      );
    case "portfolio":
      return <PortfolioView dataMode={props.dataMode} />;
    case "filings":
      return (
        <FilingsView
          searchSelection={props.searchSelection}
          dataMode={props.dataMode}
          addFavorite={props.addFavorite}
          isFavorited={props.isFavorited}
          goToView={(view) => props.goToView(view)}
          setSearchSelection={(selection: FilingsSearchSelection) =>
            props.setSearchSelection((current) => ({ ...current, ...selection }))
          }
        />
      );
    case "timeline":
      return (
        <TimelineView
          dataMode={props.dataMode}
          searchSelection={props.searchSelection}
          goToView={(view) => props.goToView(view)}
          setSearchSelection={(selection: TimelineChatSearchSelection) =>
            props.setSearchSelection((current) => ({ ...current, ...selection }))
          }
        />
      );
    case "news":
      return (
        <NewsView
          searchSelection={props.searchSelection}
          dataMode={props.dataMode}
          addFavorite={props.addFavorite}
          isFavorited={props.isFavorited}
          goToView={(view) => props.goToView(view)}
          setSearchSelection={(selection: NewsSearchSelection) =>
            props.setSearchSelection((current) => ({ ...current, ...selection }))
          }
        />
      );
    case "profile":
      return (
        <ProfileView
          dataMode={props.dataMode}
          theme={props.theme}
          onToggleTheme={props.onToggleTheme}
          onToggleDataMode={props.onToggleDataMode}
          pushToast={props.pushToast}
        />
      );
case "settings":
        return (
          <SettingsView
            theme={props.theme}
            dataMode={props.dataMode}
            onToggleTheme={props.onToggleTheme}
            onToggleDataMode={props.onToggleDataMode}
            favoritesCount={props.favoritesCount}
            unreadNotifications={props.unreadCount}
          />
        );

    default:
      return (
        <DashboardView
          dataMode={props.dataMode}
          preferences={props.dashboardPreferences}
          onToggleDensity={props.onToggleDashboardDensity}
          onToggleWidget={props.onToggleDashboardWidget}
          onResetPreferences={props.onResetDashboardPreferences}
        />
      );
  }
}
