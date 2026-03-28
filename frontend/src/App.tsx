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
  QUICK_QUERY_TEMPLATES,
  THEME_STORAGE_KEY,
} from "./app/constants";
import { useAlertRules } from "./app/hooks/useAlertRules";
import { useChatThreads } from "./app/hooks/useChatThreads";
import { useFavorites } from "./app/hooks/useFavorites";
import { useNotifications } from "./app/hooks/useNotifications";
import type {
  CommandItem,
  CompanySearchSelection,
  DashboardPreferences,
  DataMode,
  FavoriteItem,
  FilingsSearchSelection,
  GlobalSearchResult,
  NewsSearchSelection,
  SearchSelection,
  Theme,
  TimelineChatSearchSelection,
  ToastItem,
  ToastTone,
  ViewKey,
} from "./app/types";

type ViewTransitionCapable = {
  startViewTransition?: (updateCallback: () => void) => { finished: Promise<void> };
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
    if (parsed && (parsed.density === "comfortable" || parsed.density === "compact")) {
      return {
        density: parsed.density,
        hiddenWidgets: Array.isArray(parsed.hiddenWidgets) ? parsed.hiddenWidgets : [],
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
  const [searchSelection, setSearchSelection] = useState<SearchSelection | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [globalSearchIndex, setGlobalSearchIndex] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteActiveIndex, setPaletteActiveIndex] = useState(0);
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
      JSON.stringify(dashboardPreferences)
    );
  }, [dashboardPreferences]);

  const openGlobalSearch = useCallback(() => {
    setGlobalSearchOpen(true);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);
  }, []);

  const closeGlobalSearch = useCallback(() => {
    setGlobalSearchOpen(false);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);
  }, []);

  const toggleTheme = useCallback(() => {
    const root = document.documentElement;
    const startViewTransition = (document as unknown as ViewTransitionCapable).startViewTransition;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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
      pushToast(next === "demo" ? "Demo mode enabled" : "Live API mode enabled", "info");
      return next;
    });
  }, [pushToast]);

  const goToView = useCallback((view: ViewKey) => {
    setActiveView(view);
    setPaletteOpen(false);
    setPaletteQuery("");
    setPaletteActiveIndex(0);
    setGlobalSearchOpen(false);
    setGlobalSearchQuery("");
    setGlobalSearchIndex(0);

    if (view === "filings") {
      createNotification({
        title: "Filings workspace opened",
        message: "Track new regulatory disclosures and key updates from one place.",
        category: "filing",
        severity: "low",
      });
    }

    if (view === "news") {
      createNotification({
        title: "News radar opened",
        message: "Sentiment and headline monitoring is now active for quick scanning.",
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
  }, [createNotification]);

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
    [goToView, pushToast, setFavoritesOpen]
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

  const globalSearchResults = useMemo<GlobalSearchResult[]>(() => {
    const query = globalSearchQuery.trim().toLowerCase();
    const results: GlobalSearchResult[] = [];

    if (!query) {
      results.push(
        {
          id: "hint-company",
          type: "company",
          title: "Search company symbols",
          subtitle: "Examples: RELIANCE, TCS, INFY",
          onSelect: () => {
            setSearchSelection({ stamp: Date.now(), discoveryQuery: "RELIANCE" });
            goToView("discovery");
          },
        },
        {
          id: "hint-theme",
          type: "theme",
          title: "Jump to themes",
          subtitle: "Examples: AI, Defense, Renewable",
          onSelect: () => {
            setSearchSelection({ stamp: Date.now(), discoveryTheme: "AI" });
            goToView("discovery");
          },
        },
        {
          id: "hint-query",
          type: "query",
          title: "Ask Iris quickly",
          subtitle: "Open chat with a prepared prompt",
          onSelect: () => {
            setSearchSelection({
              stamp: Date.now(),
              chatPrompt: "Summarize portfolio risk in simple language.",
            });
            goToView("chat");
          },
        }
      );
      return results;
    }

    results.push({
      id: `search-${query}`,
      type: "company",
      title: `Search: ${query}`,
      subtitle: "Search company database",
      onSelect: () => {
        setSearchSelection({ stamp: Date.now(), discoveryQuery: query });
        goToView("discovery");
      },
    });

    for (const template of QUICK_QUERY_TEMPLATES) {
      if (!template.toLowerCase().includes(query)) continue;
      results.push({
        id: `query-${template}`,
        type: "query",
        title: template,
        subtitle: "Use as chat starter",
        onSelect: () => {
          setSearchSelection({ stamp: Date.now(), chatPrompt: template });
          goToView("chat");
        },
      });
    }

    return results.slice(0, 18);
  }, [globalSearchQuery, goToView]);

  const openPalette = useCallback(() => {
    setPaletteOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    setPaletteOpen(false);
    setPaletteQuery("");
    setPaletteActiveIndex(0);
  }, []);

  const paletteCommands = useMemo<CommandItem[]>(
    () => [
      {
        id: "go-dashboard",
        label: "Go to Dashboard",
        hint: "Navigation",
        keywords: "dashboard home overview",
        action: () => goToView("dashboard"),
      },
      {
        id: "go-compare",
        label: "Go to Comparison Workspace",
        hint: "Navigation",
        keywords: "compare side by side symbols",
        action: () => {
          setSearchSelection({ stamp: Date.now(), compareSymbols: ["RELIANCE", "TCS"] });
          goToView("compare");
        },
      },
      {
        id: "go-company",
        label: "Go to Company Workspace",
        hint: "Navigation",
        keywords: "company workspace symbol details",
        action: () => {
          setSearchSelection({ stamp: Date.now(), companySymbol: "RELIANCE" });
          goToView("company");
        },
      },
      {
        id: "go-company-from-context",
        label: "Open Company from Current Context",
        hint: "Navigation",
        keywords: "company current symbol context",
        action: () => {
          const symbol =
            searchSelection?.companySymbol ??
            searchSelection?.filingsSymbol ??
            searchSelection?.newsSymbol ??
            searchSelection?.discoveryQuery ??
            "RELIANCE";
          setSearchSelection({ stamp: Date.now(), companySymbol: symbol });
          goToView("company");
        },
      },
      {
        id: "go-chat",
        label: "Go to Iris Chat",
        hint: "Navigation",
        keywords: "chat copilot iris assistant",
        action: () => goToView("chat"),
      },
      {
        id: "go-discovery",
        label: "Go to Discovery",
        hint: "Navigation",
        keywords: "discovery themes ai defense sectors",
        action: () => goToView("discovery"),
      },
      {
        id: "go-portfolio",
        label: "Go to Portfolio",
        hint: "Navigation",
        keywords: "portfolio holdings risk exposure",
        action: () => goToView("portfolio"),
      },
      {
        id: "go-timeline",
        label: "Go to Timeline",
        hint: "Navigation",
        keywords: "timeline feed events filings history",
        action: () => goToView("timeline"),
      },
      {
        id: "go-filings",
        label: "Go to Filings",
        hint: "Navigation",
        keywords: "filings sec reports documents",
        action: () => goToView("filings"),
      },
      {
        id: "go-news",
        label: "Go to News & Sentiment",
        hint: "Navigation",
        keywords: "news sentiment headlines",
        action: () => goToView("news"),
      },
      {
        id: "go-settings",
        label: "Go to Settings",
        hint: "Navigation",
        keywords: "settings preferences configuration",
        action: () => goToView("settings"),
      },
      {
        id: "toggle-theme",
        label: theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme",
        hint: "Appearance",
        keywords: "theme light dark appearance",
        action: () => {
          toggleTheme();
          closePalette();
        },
      },
      {
        id: "toggle-data-mode",
        label: dataMode === "demo" ? "Switch to Live API Mode" : "Switch to Demo Data Mode",
        hint: "Data",
        keywords: "demo mock live api data mode",
        action: () => {
          toggleDataMode();
          closePalette();
        },
      },
      {
        id: "open-alert-rules",
        label: "Open Alert Rules Builder",
        hint: "Automation",
        keywords: "alert rules automation triggers notifications",
        action: () => {
          setAlertRulesOpen(true);
          closePalette();
        },
      },
      {
        id: "run-alert-check",
        label: "Run Alert Rules Check",
        hint: "Automation",
        keywords: "alert evaluate check now",
        action: () => {
          runAlertRulesCheck();
          closePalette();
        },
      },
      {
        id: "open-notifications",
        label: "Open Notifications",
        hint: "Inbox",
        keywords: "notifications alerts inbox bell",
        action: () => {
          setNotificationsOpen(true);
          closePalette();
        },
      },
      {
        id: "mark-all-read",
        label: "Mark All Notifications Read",
        hint: "Inbox",
        keywords: "notifications read clear alerts",
        action: () => {
          markAllNotificationsRead();
          closePalette();
        },
      },
    ],
    [
      closePalette,
      goToView,
      markAllNotificationsRead,
      runAlertRulesCheck,
      setAlertRulesOpen,
      setNotificationsOpen,
      searchSelection?.companySymbol,
      searchSelection?.discoveryQuery,
      searchSelection?.filingsSymbol,
      searchSelection?.newsSymbol,
      dataMode,
      theme,
      toggleDataMode,
      toggleTheme,
    ]
  );

  const filteredCommands = useMemo(() => {
    const query = paletteQuery.trim().toLowerCase();
    if (!query) return paletteCommands;

    return paletteCommands.filter((command) => {
      const haystack = `${command.label} ${command.keywords} ${command.hint ?? ""}`.toLowerCase();
      return haystack.includes(query);
    });
  }, [paletteCommands, paletteQuery]);

  useEffect(() => {
    if (!paletteOpen) return;
    window.requestAnimationFrame(() => {
      paletteInputRef.current?.focus();
    });
  }, [paletteOpen]);

  useEffect(() => {
    if (!globalSearchOpen) return;
    window.requestAnimationFrame(() => {
      globalSearchInputRef.current?.focus();
    });
  }, [globalSearchOpen]);

  useEffect(() => {
    setPaletteActiveIndex(0);
  }, [paletteQuery]);

  useEffect(() => {
    setGlobalSearchIndex(0);
  }, [globalSearchQuery]);

  useEffect(() => {
    const handleGlobalShortcuts = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTypingContext =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setGlobalSearchOpen((current) => {
          if (current) {
            setGlobalSearchQuery("");
            setGlobalSearchIndex(0);
            return false;
          }
          return true;
        });
        return;
      }

      if (globalSearchOpen) {
        if (event.key === "Escape") {
          event.preventDefault();
          closeGlobalSearch();
          return;
        }

        if (event.key === "ArrowDown") {
          event.preventDefault();
          setGlobalSearchIndex((current) =>
            globalSearchResults.length ? (current + 1) % globalSearchResults.length : 0
          );
          return;
        }

        if (event.key === "ArrowUp") {
          event.preventDefault();
          setGlobalSearchIndex((current) =>
            globalSearchResults.length
              ? (current - 1 + globalSearchResults.length) % globalSearchResults.length
              : 0
          );
          return;
        }

        if (event.key === "Enter") {
          event.preventDefault();
          const result = globalSearchResults[globalSearchIndex] ?? globalSearchResults[0];
          result?.onSelect();
        }
        return;
      }

      if (!paletteOpen) return;

      if (isTypingContext) {
        if (event.key === "Escape") {
          event.preventDefault();
          closePalette();
        }
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        closePalette();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        setPaletteActiveIndex((current) =>
          filteredCommands.length ? (current + 1) % filteredCommands.length : 0
        );
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        setPaletteActiveIndex((current) =>
          filteredCommands.length
            ? (current - 1 + filteredCommands.length) % filteredCommands.length
            : 0
        );
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        const command = filteredCommands[paletteActiveIndex];
        command?.action();
      }
    };

    window.addEventListener("keydown", handleGlobalShortcuts);
    return () => {
      window.removeEventListener("keydown", handleGlobalShortcuts);
    };
  }, [
    closeGlobalSearch,
    closePalette,
    filteredCommands,
    globalSearchIndex,
    globalSearchOpen,
    globalSearchResults,
    paletteActiveIndex,
    paletteOpen,
  ]);

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
