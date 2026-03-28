import { useEffect } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { CommandItem, GlobalSearchResult } from "../types";

interface UseGlobalShortcutsOptions {
  paletteOpen: boolean;
  setPaletteOpen: Dispatch<SetStateAction<boolean>>;
  closePalette: () => void;
  filteredCommands: CommandItem[];
  paletteActiveIndex: number;
  setPaletteActiveIndex: Dispatch<SetStateAction<number>>;
  setGlobalSearchOpen: Dispatch<SetStateAction<boolean>>;
  setGlobalSearchQuery: Dispatch<SetStateAction<string>>;
  setGlobalSearchIndex: Dispatch<SetStateAction<number>>;
  globalSearchOpen: boolean;
  closeGlobalSearch: () => void;
  globalSearchResults: GlobalSearchResult[];
  globalSearchIndex: number;
}

export function useGlobalShortcuts(options: UseGlobalShortcutsOptions) {
  useEffect(() => {
    const handleGlobalShortcuts = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isTypingContext =
        target?.tagName === "INPUT" ||
        target?.tagName === "TEXTAREA" ||
        target?.isContentEditable;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        options.setPaletteOpen((current) => !current);
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "j") {
        event.preventDefault();
        options.setGlobalSearchOpen((current) => {
          if (current) {
            options.setGlobalSearchQuery("");
            options.setGlobalSearchIndex(0);
            return false;
          }
          return true;
        });
        return;
      }

      if (options.globalSearchOpen) {
        if (event.key === "Escape") {
          event.preventDefault();
          options.closeGlobalSearch();
          return;
        }

        if (event.key === "ArrowDown") {
          event.preventDefault();
          options.setGlobalSearchIndex((current) =>
            options.globalSearchResults.length ? (current + 1) % options.globalSearchResults.length : 0
          );
          return;
        }

        if (event.key === "ArrowUp") {
          event.preventDefault();
          options.setGlobalSearchIndex((current) =>
            options.globalSearchResults.length
              ? (current - 1 + options.globalSearchResults.length) % options.globalSearchResults.length
              : 0
          );
          return;
        }

        if (event.key === "Enter") {
          event.preventDefault();
          const result = options.globalSearchResults[options.globalSearchIndex] ?? options.globalSearchResults[0];
          result?.onSelect();
        }
        return;
      }

      if (!options.paletteOpen) return;

      if (isTypingContext) {
        if (event.key === "Escape") {
          event.preventDefault();
          options.closePalette();
        }
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        options.closePalette();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        options.setPaletteActiveIndex((current) =>
          options.filteredCommands.length ? (current + 1) % options.filteredCommands.length : 0
        );
        return;
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        options.setPaletteActiveIndex((current) =>
          options.filteredCommands.length
            ? (current - 1 + options.filteredCommands.length) % options.filteredCommands.length
            : 0
        );
        return;
      }

      if (event.key === "Enter") {
        event.preventDefault();
        const command = options.filteredCommands[options.paletteActiveIndex];
        command?.action();
      }
    };

    window.addEventListener("keydown", handleGlobalShortcuts);
    return () => {
      window.removeEventListener("keydown", handleGlobalShortcuts);
    };
  }, [
    options.closeGlobalSearch,
    options.closePalette,
    options.filteredCommands,
    options.globalSearchIndex,
    options.globalSearchOpen,
    options.globalSearchResults,
    options.paletteActiveIndex,
    options.paletteOpen,
    options.setGlobalSearchIndex,
    options.setGlobalSearchOpen,
    options.setGlobalSearchQuery,
    options.setPaletteActiveIndex,
    options.setPaletteOpen,
  ]);
}
