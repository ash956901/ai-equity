import { useCallback, useEffect, useMemo, useState } from "react";
import { DashboardView } from "./features/dashboard/DashboardView";
import { SettingsView } from "./features/settings/SettingsView";
import { DiscoveryView } from "./features/discovery/DiscoveryView";
import { TimelineView } from "./features/timeline/TimelineView";
import { PortfolioView } from "./features/portfolio/PortfolioView";
import { FilingsView } from "./features/filings/FilingsView";
import { NewsView } from "./features/news/NewsView";
import { ProfileView } from "./features/profile/ProfileView";
import { ComparisonWorkspaceView } from "./features/compare/ComparisonWorkspaceView";
import { ChatView } from "./features/chat/ChatView";
import { CompanyWorkspaceView } from "./features/company/CompanyWorkspaceView";

import { NotificationsPanel } from "./app/components/NotificationsPanel";
import { ToastStack } from "./app/components/ToastStack";
import { SidebarShell } from "./app/components/SidebarShell";
import {
  DASHBOARD_PREFERENCES_KEY,
  DEMO_BANNER_MSG,
  THEME_STORAGE_KEY,
} from "./app/constants";
import { useChatThreads } from "./app/hooks/useChatThreads";
import { useNotifications } from "./app/hooks/useNotifications";
import type {
  CompanySearchSelection,
  DashboardPreferences,
  FilingsSearchSelection,
  NewsSearchSelection,
  SearchSelection,
  Theme,
  TimelineChatSearchSelection,
  ToastItem,
  ToastTone,
  ViewKey,
} from "./app/types";

type ViewTransitionCapable = {
  startViewTransition?: (updateCallback: () => void) => {
    finished: Promise<void>;
  };
};

function getInitialTheme(): Theme {
  const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
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
    if (
      parsed &&
      (parsed.density === "comfortable" || parsed.density === "compact")
    ) {
      return {
        density: parsed.density,
        hiddenWidgets: Array.isArray(parsed.hiddenWidgets)
          ? parsed.hiddenWidgets
          : [],
      };
    }
    return { density: "comfortable", hiddenWidgets: [] };
  } catch {
    return { density: "comfortable", hiddenWidgets: [] };
  }
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>("home");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const dataMode = "live";
  const [dashboardPreferences, setDashboardPreferences] =
    useState<DashboardPreferences>(getInitialDashboardPreferences);
  const [searchSelection, setSearchSelection] =
    useState<SearchSelection | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

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

  const {
    notificationsOpen,
    setNotificationsOpen,
    notificationFilter,
    setNotificationFilter,
    unreadCount,
    filteredNotifications,
    markAllNotificationsRead,
    markNotificationRead,
    dismissNotification,
    createNotification,
  } = useNotifications({ pushToast });

  const {
    chatThreads,
    setChatThreads,
    activeChatThreadId,
    setActiveChatThreadId,
    createInitialThread,
  } = useChatThreads();

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    root.classList.toggle("theme-dark", theme === "dark");
    root.classList.toggle("theme-light", theme === "light");
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(
      DASHBOARD_PREFERENCES_KEY,
      JSON.stringify(dashboardPreferences),
    );
  }, [dashboardPreferences]);

 
  const toggleTheme = useCallback(() => {
    const root = document.documentElement;
    const startViewTransition = (document as unknown as ViewTransitionCapable)
      .startViewTransition;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
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
    // Disabled in UI
  }, []);

  const addFavorite = useCallback(() => {
    // Disabled in UI
  }, []);

  const isFavorited = useCallback(() => {
    return false;
  }, []);

  const goToView = useCallback(
    (view: ViewKey) => {
      setActiveView(view);

      if (view === "filings") {
        createNotification({
          title: "Filings workspace opened",
          message:
            "Track new regulatory disclosures and key updates from one place.",
          category: "filing",
          severity: "low",
        });
      }

      if (view === "news") {
        createNotification({
          title: "News radar opened",
          message:
            "Sentiment and headline monitoring is now active for quick scanning.",
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
    },
    [createNotification],
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
            createInitialThread={createInitialThread}
            demoBannerMessage={DEMO_BANNER_MSG}
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
            favoritesCount={0}
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
    goToView,
    isFavorited,
    pushToast,
    resetDashboardPreferences,
    searchSelection,
    setActiveChatThreadId,
    setChatThreads,
    chatThreads,
    theme,
    toggleDashboardDensity,
    toggleDashboardWidget,
    toggleDataMode,
    toggleTheme,
    unreadCount,
    createInitialThread,
  ]);

  return (
    <div className="app-shell">
      <SidebarShell
        activeView={activeView}
        unreadCount={unreadCount}
        theme={theme}
        onOpenNotifications={() => setNotificationsOpen(true)}
        onToggleTheme={toggleTheme}
        onGoToView={goToView}
        onPickCompany={(ticker, companyId) => {
          setSearchSelection({
            stamp: Date.now(),
            companySymbol: ticker,
            companyId,
          });
          goToView("company");
        }}
      />

      <main className="main-panel">{page}</main>

      <NotificationsPanel
        open={notificationsOpen}
        filter={notificationFilter}
        notifications={filteredNotifications}
        onClose={() => setNotificationsOpen(false)}
        onFilterChange={setNotificationFilter}
        onMarkAllRead={markAllNotificationsRead}
        onMarkRead={markNotificationRead}
        onDismiss={dismissNotification}
      />

      <ToastStack toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
