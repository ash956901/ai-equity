import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { CommandPalette } from "./app/components/CommandPalette";
import { GlobalSearchOverlay } from "./app/components/GlobalSearchOverlay";
import { NotificationsPanel } from "./app/components/NotificationsPanel";
import { FavoritesPanel } from "./app/components/FavoritesPanel";
import { AlertRulesPanel } from "./app/components/AlertRulesPanel";
import { ToastStack } from "./app/components/ToastStack";
import { SidebarShell } from "./app/components/SidebarShell";
import {
  DASHBOARD_PREFERENCES_KEY,
  DATA_MODE_STORAGE_KEY,
  DEMO_BANNER_MSG,
  THEME_STORAGE_KEY,
} from "./app/constants";
import { useAlertRules } from "./app/hooks/useAlertRules";
import { useChatThreads } from "./app/hooks/useChatThreads";
import { useFavorites } from "./app/hooks/useFavorites";
import { useNotifications } from "./app/hooks/useNotifications";
import { usePaletteSearch } from "./app/hooks/usePaletteSearch";
import { useGlobalShortcuts } from "./app/hooks/useGlobalShortcuts";
import type {
  CompanySearchSelection,
  DashboardPreferences,
  DataMode,
  FavoriteItem,
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

function getInitialDataMode(): DataMode {
  const saved = window.localStorage.getItem(DATA_MODE_STORAGE_KEY);
  if (saved === "live" || saved === "demo") return saved;
  return "live";
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
  const [activeView, setActiveView] = useState<ViewKey>("dashboard");
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [dataMode, setDataMode] = useState<DataMode>(getInitialDataMode);
  const [dashboardPreferences, setDashboardPreferences] =
    useState<DashboardPreferences>(getInitialDashboardPreferences);
  const [searchSelection, setSearchSelection] =
    useState<SearchSelection | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  // Palette and Global Search state are now managed by usePaletteSearch hook
  // The input refs are still needed for focusing the inputs
  const paletteInputRef = useRef<HTMLInputElement | null>(null);
  const globalSearchInputRef = useRef<HTMLInputElement | null>(null);

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
    favorites,
    setFavorites,
    favoritesOpen,
    setFavoritesOpen,
    favoriteFilter,
    setFavoriteFilter,
    filteredFavorites,
    addFavorite,
    removeFavorite,
    isFavorited,
  } = useFavorites({ pushToast });

  const {
    alertRules,
    alertRulesOpen,
    setAlertRulesOpen,
    ruleName,
    setRuleName,
    ruleType,
    setRuleType,
    ruleSymbol,
    setRuleSymbol,
    ruleThreshold,
    setRuleThreshold,
    activeRulesCount,
    createAlertRule,
    toggleAlertRule,
    deleteAlertRule,
    runAlertRulesCheck,
  } = useAlertRules({ pushToast });

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
    window.localStorage.setItem(DATA_MODE_STORAGE_KEY, dataMode);
  }, [dataMode]);

  useEffect(() => {
    window.localStorage.setItem(
      DASHBOARD_PREFERENCES_KEY,
      JSON.stringify(dashboardPreferences),
    );
  }, [dashboardPreferences]);

  // openGlobalSearch and closeGlobalSearch are provided by the usePaletteSearch hook

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
    setDataMode((current) => {
      const next = current === "live" ? "demo" : "live";
      pushToast(
        next === "demo" ? "Demo mode enabled" : "Live API mode enabled",
        "info",
      );
      return next;
    });
  }, [pushToast]);

  // Navigation helper – UI state (palette / global search) is handled by the palette/search hook
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

  const handleFavoriteSelect = useCallback(
    (favorite: FavoriteItem) => {
      if (favorite.type === "company") {
        setSearchSelection({
          stamp: Date.now(),
          discoveryQuery: favorite.symbol ?? favorite.title,
          filingsSymbol: favorite.symbol,
          newsSymbol: favorite.symbol,
        });
        goToView("discovery");
      } else if (favorite.type === "filing") {
        setSearchSelection({
          stamp: Date.now(),
          filingsSymbol: favorite.symbol,
          discoveryQuery: favorite.symbol,
        });
        goToView("filings");
      } else {
        setSearchSelection({
          stamp: Date.now(),
          newsSymbol: favorite.symbol,
        });
        goToView("news");
      }

      setFavoritesOpen(false);
      pushToast("Opened from favorites", "info");
    },
    [goToView, pushToast, setFavoritesOpen],
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

  // Palette and Global Search state & logic are now provided by usePaletteSearch
  const {
    globalSearchOpen,
    globalSearchQuery,
    globalSearchIndex,
    setGlobalSearchOpen,
    setGlobalSearchQuery,
    setGlobalSearchIndex,
    openGlobalSearch,
    closeGlobalSearch,
    globalSearchResults,
    paletteOpen,
    paletteQuery,
    paletteActiveIndex,
    setPaletteOpen,
    setPaletteQuery,
    setPaletteActiveIndex,
    openPalette,
    closePalette,
    filteredCommands,
  } = usePaletteSearch({
    searchSelection,
    goToView,
    setSearchSelection,
    theme,
    dataMode,
    toggleTheme,
    toggleDataMode,
    runAlertRulesCheck,
    markAllNotificationsRead,
    setAlertRulesOpen,
    setNotificationsOpen,
  });

  // Keyboard shortcuts handling
  useGlobalShortcuts({
    paletteOpen,
    setPaletteOpen,
    closePalette,
    filteredCommands,
    paletteActiveIndex,
    setPaletteActiveIndex,
    setGlobalSearchOpen,
    setGlobalSearchQuery,
    setGlobalSearchIndex,
    globalSearchOpen,
    closeGlobalSearch,
    globalSearchResults,
    globalSearchIndex,
  });



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
            favoritesCount={favorites.length}
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
    favorites.length,
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
        activeRulesCount={activeRulesCount}
        favoritesCount={favorites.length}
        theme={theme}
        dataMode={dataMode}
        onOpenNotifications={() => setNotificationsOpen(true)}
        onOpenAlertRules={() => setAlertRulesOpen(true)}
        onOpenFavorites={() => setFavoritesOpen(true)}
        onClearFavorites={() => {
          setFavorites([]);
          pushToast("Favorites cleared", "info");
        }}
        onToggleTheme={toggleTheme}
        onToggleDataMode={toggleDataMode}
        onOpenPalette={openPalette}
        onOpenGlobalSearch={openGlobalSearch}
        onGoToView={goToView}
      />

      <main className="main-panel">{page}</main>

      <CommandPalette
        open={paletteOpen}
        query={paletteQuery}
        activeIndex={paletteActiveIndex}
        commands={filteredCommands}
        inputRef={paletteInputRef}
        setQuery={setPaletteQuery}
        setActiveIndex={setPaletteActiveIndex}
        onClose={closePalette}
      />

      <GlobalSearchOverlay
        open={globalSearchOpen}
        query={globalSearchQuery}
        activeIndex={globalSearchIndex}
        results={globalSearchResults}
        inputRef={globalSearchInputRef}
        setQuery={setGlobalSearchQuery}
        setActiveIndex={setGlobalSearchIndex}
        onClose={closeGlobalSearch}
      />

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

      <FavoritesPanel
        open={favoritesOpen}
        filter={favoriteFilter}
        favorites={filteredFavorites}
        onClose={() => setFavoritesOpen(false)}
        onFilterChange={setFavoriteFilter}
        onOpenFavorite={handleFavoriteSelect}
        onRemoveFavorite={removeFavorite}
      />

      <AlertRulesPanel
        open={alertRulesOpen}
        rules={alertRules}
        ruleName={ruleName}
        ruleType={ruleType}
        ruleSymbol={ruleSymbol}
        ruleThreshold={ruleThreshold}
        onClose={() => setAlertRulesOpen(false)}
        onRuleNameChange={setRuleName}
        onRuleTypeChange={setRuleType}
        onRuleSymbolChange={setRuleSymbol}
        onRuleThresholdChange={setRuleThreshold}
        onCreateRule={createAlertRule}
        onRunCheck={runAlertRulesCheck}
        onToggleRule={toggleAlertRule}
        onDeleteRule={deleteAlertRule}
      />

      <ToastStack toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
