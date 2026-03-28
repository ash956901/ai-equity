import { useCallback, useMemo, useState } from "react";

import { FAVORITES_STORAGE_KEY } from "../constants";
import type { FavoriteItem, FavoriteType, ToastTone } from "../types";
import { usePersistentState } from "./usePersistentState";

function getInitialFavorites(): FavoriteItem[] {
  const saved = window.localStorage.getItem(FAVORITES_STORAGE_KEY);
  if (!saved) return [];

  try {
    const parsed = JSON.parse(saved) as FavoriteItem[];
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return [];
  } catch {
    return [];
  }
}

interface UseFavoritesOptions {
  pushToast: (message: string, tone?: ToastTone) => void;
}

export function useFavorites(options: UseFavoritesOptions) {
  const [favorites, setFavorites] = usePersistentState<FavoriteItem[]>(
    FAVORITES_STORAGE_KEY,
    getInitialFavorites
  );
  const [favoritesOpen, setFavoritesOpen] = useState(false);
  const [favoriteFilter, setFavoriteFilter] = useState<"all" | FavoriteType>("all");

  const filteredFavorites = useMemo(
    () =>
      favorites.filter((favorite) =>
        favoriteFilter === "all" ? true : favorite.type === favoriteFilter
      ),
    [favoriteFilter, favorites]
  );

  const addFavorite = useCallback(
    (favorite: Omit<FavoriteItem, "id" | "createdAt">) => {
      const key = `${favorite.type}::${favorite.title}::${favorite.symbol ?? ""}`.toLowerCase();

      setFavorites((current) => {
        const exists = current.some(
          (item) => `${item.type}::${item.title}::${item.symbol ?? ""}`.toLowerCase() === key
        );

        if (exists) {
          options.pushToast("Already in favorites", "info");
          return current;
        }

        const next: FavoriteItem = {
          ...favorite,
          id: `fav-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          createdAt: new Date().toISOString(),
        };

        options.pushToast("Saved to favorites", "success");
        return [next, ...current].slice(0, 120);
      });
    },
    [options, setFavorites]
  );

  const removeFavorite = useCallback(
    (id: string) => {
      setFavorites((current) => current.filter((item) => item.id !== id));
      options.pushToast("Removed from favorites", "info");
    },
    [options, setFavorites]
  );

  const isFavorited = useCallback(
    (favorite: Pick<FavoriteItem, "type" | "title" | "symbol">) => {
      const key = `${favorite.type}::${favorite.title}::${favorite.symbol ?? ""}`.toLowerCase();
      return favorites.some(
        (item) => `${item.type}::${item.title}::${item.symbol ?? ""}`.toLowerCase() === key
      );
    },
    [favorites]
  );

  return {
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
  };
}
