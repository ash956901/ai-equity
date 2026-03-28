import {
  useCallback,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import { QUICK_QUERY_TEMPLATES } from "../constants";
import type {
  CommandItem,
  DataMode,
  GlobalSearchResult,
  SearchSelection,
  Theme,
  ViewKey,
} from "../types";

interface UsePaletteSearchOptions {
  searchSelection: SearchSelection | null;
  goToView: (view: ViewKey) => void;
  setSearchSelection: Dispatch<SetStateAction<SearchSelection | null>>;
  theme: Theme;
  dataMode: DataMode;
  toggleTheme: () => void;
  toggleDataMode: () => void;
  runAlertRulesCheck: () => void;
  markAllNotificationsRead: () => void;
  setAlertRulesOpen: Dispatch<SetStateAction<boolean>>;
  setNotificationsOpen: Dispatch<SetStateAction<boolean>>;
}

interface UsePaletteSearchResult {
  globalSearchOpen: boolean;
  globalSearchQuery: string;
  globalSearchIndex: number;
  setGlobalSearchOpen: Dispatch<SetStateAction<boolean>>;
  setGlobalSearchQuery: Dispatch<SetStateAction<string>>;
  setGlobalSearchIndex: Dispatch<SetStateAction<number>>;
  openGlobalSearch: () => void;
  closeGlobalSearch: () => void;
  globalSearchResults: GlobalSearchResult[];
  paletteOpen: boolean;
  paletteQuery: string;
  paletteActiveIndex: number;
  setPaletteOpen: Dispatch<SetStateAction<boolean>>;
  setPaletteQuery: Dispatch<SetStateAction<string>>;
  setPaletteActiveIndex: Dispatch<SetStateAction<number>>;
  openPalette: () => void;
  closePalette: () => void;
  filteredCommands: CommandItem[];
}

export function usePaletteSearch(options: UsePaletteSearchOptions): UsePaletteSearchResult {
  const {
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
  } = options;

  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
  const [globalSearchQuery, setGlobalSearchQuery] = useState("");
  const [globalSearchIndex, setGlobalSearchIndex] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteActiveIndex, setPaletteActiveIndex] = useState(0);

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

  const openPalette = useCallback(() => {
    setPaletteOpen(true);
  }, []);

  const closePalette = useCallback(() => {
    setPaletteOpen(false);
    setPaletteQuery("");
    setPaletteActiveIndex(0);
  }, []);

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
            closeGlobalSearch();
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
            closeGlobalSearch();
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
            closeGlobalSearch();
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
        closeGlobalSearch();
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
          closeGlobalSearch();
        },
      });
    }

    return results.slice(0, 18);
  }, [globalSearchQuery, goToView, setSearchSelection]);

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
          closePalette();
          closeGlobalSearch();
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
          closePalette();
          closeGlobalSearch();
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
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-chat",
        label: "Go to Iris Chat",
        hint: "Navigation",
        keywords: "chat copilot iris assistant",
        action: () => {
          goToView("chat");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-discovery",
        label: "Go to Discovery",
        hint: "Navigation",
        keywords: "discovery themes ai defense sectors",
        action: () => {
          goToView("discovery");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-portfolio",
        label: "Go to Portfolio",
        hint: "Navigation",
        keywords: "portfolio holdings risk exposure",
        action: () => {
          goToView("portfolio");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-timeline",
        label: "Go to Timeline",
        hint: "Navigation",
        keywords: "timeline feed events filings history",
        action: () => {
          goToView("timeline");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-filings",
        label: "Go to Filings",
        hint: "Navigation",
        keywords: "filings sec reports documents",
        action: () => {
          goToView("filings");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-news",
        label: "Go to News & Sentiment",
        hint: "Navigation",
        keywords: "news sentiment headlines",
        action: () => {
          goToView("news");
          closePalette();
          closeGlobalSearch();
        },
      },
      {
        id: "go-settings",
        label: "Go to Settings",
        hint: "Navigation",
        keywords: "settings preferences configuration",
        action: () => {
          goToView("settings");
          closePalette();
          closeGlobalSearch();
        },
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
      dataMode,
      goToView,
      markAllNotificationsRead,
      runAlertRulesCheck,
      searchSelection?.companySymbol,
      searchSelection?.discoveryQuery,
      searchSelection?.filingsSymbol,
      searchSelection?.newsSymbol,
      setAlertRulesOpen,
      setNotificationsOpen,
      setSearchSelection,
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

  return {
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
  };
}
